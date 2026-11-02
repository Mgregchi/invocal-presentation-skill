#!/usr/bin/env python3
"""Build narration-first timing, encode frames, and verify the encoded output."""
import argparse
import hashlib
import importlib.util
import io
import json
import math
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def run(args):
    result = subprocess.run([str(x) for x in args], capture_output=True)
    require(result.returncode == 0, 'Command failed: ' + str(args[0]) + '\n' + result.stderr.decode(errors='replace')[-2500:])
    return result.stdout


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unwrap(value):
    if isinstance(value, dict) and value.get('isError'):
        raise ValueError('MCP returned an error; resolve it before production')
    if isinstance(value, dict) and value.get('structuredContent') is not None:
        return unwrap(value['structuredContent'])
    if isinstance(value, dict) and 'content' in value:
        for block in value['content']:
            if block.get('type') == 'text':
                try:
                    return unwrap(json.loads(block['text']))
                except json.JSONDecodeError:
                    continue
        raise ValueError('MCP response contains no JSON result')
    return value


def resolve(base, name):
    return (base / name).resolve()


def norm(token):
    return re.sub(r'[^\w]', '', token.casefold())


def anchor_time(words, anchor):
    if anchor is None or anchor == 'START':
        return 0.0
    if isinstance(anchor, str):
        anchor = {'phrase': anchor}
    require(isinstance(anchor, dict), 'Anchor must be START, a phrase, or an object')
    if 'word_index' in anchor:
        index = anchor['word_index']
        require(isinstance(index, int) and 0 <= index < len(words), 'Invalid word_index')
        return words[index]['start']
    tokens = [norm(w['text']) for w in words]
    phrase = [norm(x) for x in anchor['phrase'].split()]
    require(phrase and all(phrase), 'Empty phrase anchor')
    matches = [i for i in range(len(tokens) - len(phrase) + 1) if tokens[i:i+len(phrase)] == phrase]
    require(matches, 'Anchor not found: ' + anchor['phrase'])
    if 'occurrence' in anchor:
        n = anchor['occurrence']
        require(isinstance(n, int) and 1 <= n <= len(matches), 'Invalid anchor occurrence: ' + anchor['phrase'])
        index = matches[n - 1]
    else:
        require(len(matches) == 1, 'Ambiguous anchor; use a unique phrase or occurrence: ' + anchor['phrase'])
        index = matches[0]
    return float(words[index]['start'])


def inspect_wav(path):
    with wave.open(str(path), 'rb') as w:
        fmt = (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getcomptype())
        require(fmt == (1, 2, 24000, 'NONE'), 'Expected 24 kHz mono 16-bit PCM: ' + str(path))
        frames = w.getnframes()
        pcm = w.readframes(frames)
        require(len(pcm) == frames * 2 and frames > 0, 'Truncated/empty WAV: ' + str(path))
    header = Path(path).read_bytes()[:12]
    require(header[:4] == b'RIFF' and header[8:12] == b'WAVE', 'Invalid RIFF/WAVE header')
    return pcm, frames / 24000.0


def stamp(seconds):
    ms = round(seconds * 1000)
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'


def prepare(project_path, build_dir):
    project_path = Path(project_path).resolve()
    base = project_path.parent
    build = Path(build_dir).resolve()
    build.mkdir(parents=True, exist_ok=True)
    require(not (build / 'manifest.json').exists(), 'Use a fresh build directory for each revision')
    project = read(project_path)
    fps = project.get('fps', 25)
    width, height = project.get('resolution', [1920, 1080])
    require(isinstance(fps, int) and 1 <= fps <= 60, 'fps must be an integer from 1 to 60')
    require(width > 0 and height > 0 and width % 2 == 0 and height % 2 == 0, 'Use positive even output dimensions')
    gap = float(project.get('section_gap_seconds', .65))
    hold = float(project.get('credits_hold_seconds', 8))
    require(gap >= 0 and hold >= 0, 'Negative pause')
    sections = []
    chunks = []
    start = 0.0
    section_map = {}
    for section in project['sections']:
        sid = section['id']
        require(bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', sid)), 'Use safe alphanumeric section IDs')
        require(sid not in section_map, 'Duplicate section ID')
        require(section.get('job_id') and section.get('script'), 'Preserve job_id and exact narration script')
        pcm, duration = inspect_wav(resolve(base, section['wav']))
        job = unwrap(read(resolve(base, section['job_metadata'])))
        require(job.get('status') == 'completed', 'Invocal job is not completed')
        require(job.get('id', section['job_id']) == section['job_id'], 'Job ID mismatch')
        require(abs(duration - float(job['duration'])) <= 1/24000, 'WAV/job duration mismatch')
        raw_pages = section['timeline'] if isinstance(section['timeline'], list) else [section['timeline']]
        pages = [unwrap(read(resolve(base, p))) for p in raw_pages]
        words = []
        expected = 0
        for n, page in enumerate(pages):
            require(page.get('job_id', section['job_id']) == section['job_id'], 'Timeline/job mismatch')
            require(page.get('timingMethod') == 'azure-sdk-word-boundary', 'Actual Azure word-boundary timing required')
            require(page.get('offset', 0) == expected, 'Missing/overlapping timeline page')
            words.extend(page['words'])
            expected += len(page['words'])
            require(bool(page.get('hasMore', False)) == (n < len(pages)-1), 'Incomplete or extra timeline pages')
        require(len(words) == int(pages[0]['wordCount']) and words, 'Incomplete word timeline')
        last = -1.0
        for word in words:
            require(0 <= word['start'] <= word['end'] <= duration + .002 and word['start'] >= last, 'Invalid word times')
            last = word['start']
        item = dict(section, start=start, duration=duration, words=words,
                    wav=str(resolve(base, section['wav'])), sha256=digest(resolve(base, section['wav'])),
                    metadata=job)
        sections.append(item)
        section_map[sid] = item
        silence = bytes(round(gap * 24000) * 2)
        chunks.extend([pcm, silence])
        start += duration + len(silence)/48000
    require(sections, 'At least one narration section is required')
    narration_end = start
    # Leave at least 200 ms after narration for AAC priming/resampling at EOF.
    # This is an explicitly recorded final-frame hold, not a shifted word timeline.
    tail_guard = max(0.0, .2 - gap - hold)
    chunks.append(bytes(round((hold + tail_guard) * 24000) * 2))
    duration = start + round((hold + tail_guard) * 24000)/24000
    with wave.open(str(build / 'master.wav'), 'wb') as w:
        w.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        for chunk in chunks:
            w.writeframes(chunk)
    scenes = []
    seen_ids = set()
    for scene in project['scenes']:
        require(bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', scene['id'])), 'Use safe alphanumeric scene IDs')
        require(scene['id'] not in seen_ids, 'Duplicate scene ID')
        seen_ids.add(scene['id'])
        sec = section_map.get(scene.get('section'))
        require(sec is not None or scene.get('section') is None, 'Unknown scene section')
        scene_start = sec['start'] + anchor_time(sec['words'], scene.get('anchor', 'START')) if sec else narration_end
        elements = []
        element_ids = set()
        for element in scene.get('elements', []):
            require(element['id'] not in element_ids, 'Duplicate element ID in scene')
            element_ids.add(element['id'])
            require(element['type'] in ('text', 'image', 'outline'), 'Unsupported element type')
            x, y, w, h = element['position']
            sw, sh = project.get('slide_size', [1280, 720])
            require(min(x, y) >= 0 and min(w, h) > 0 and x+w <= sw and y+h <= sh, 'Element outside slide canvas')
            at = sec['start'] + anchor_time(sec['words'], element['anchor']) if sec and 'anchor' in element else scene_start
            until = sec['start'] + anchor_time(sec['words'], element['until_anchor']) if sec and 'until_anchor' in element else None
            item = dict(element, time=at, until=until)
            if element['type'] == 'image':
                p = resolve(base, element['src'])
                require(p.is_file(), 'Image missing: ' + str(p))
                require(element.get('attribution'), 'Image attribution/license record required')
                item['src'] = str(p)
            elements.append(item)
        scenes.append(dict(scene, start=scene_start, elements=elements))
    require(scenes and abs(scenes[0]['start']) < 1e-6, 'First scene must begin at time zero')
    require(hold == 0 or any(s.get('section') is None for s in scenes), 'Credits hold needs an explicit reference scene')
    for i, scene in enumerate(scenes):
        scene['end'] = scenes[i+1]['start'] if i+1 < len(scenes) else duration
        require(scene['end'] > scene['start'], 'Scenes must be in strictly increasing chronological order')
        for element in scene['elements']:
            require(scene['start'] <= element['time'] < scene['end'], 'Element cue outside its scene')
            require(element['until'] is None or element['time'] < element['until'] <= scene['end'], 'Invalid focus end cue')
    captions = []
    for section in sections:
        group = []
        for i, word in enumerate(section['words']):
            group.append(word)
            if len(group) >= 10 or (len(group) >= 4 and word['text'].endswith(('.', '?', '!'))) or i == len(section['words'])-1:
                tokens = [w['text'] for w in group]
                caption = ' '.join(tokens)
                if len(caption) > 63 and len(tokens) > 1:
                    split = min(range(1, len(tokens)), key=lambda n: abs(len(' '.join(tokens[:n]))-len(' '.join(tokens[n:]))))
                    caption = ' '.join(tokens[:split])+'\n'+' '.join(tokens[split:])
                captions.append(dict(start=section['start']+group[0]['start'], end=section['start']+group[-1]['end'], text=caption))
                group = []
    (build / 'captions.srt').write_text('\n\n'.join(f'{i+1}\n{stamp(c["start"])} --> {stamp(c["end"])}\n{c["text"]}' for i,c in enumerate(captions))+'\n', encoding='utf-8')
    script_text = ['# '+project['title'], '\nVoice: '+project.get('voice','en-US-JennyNeural'), '\nNarration and sources']
    for section in sections:
        script_text += ['\n## '+section['id'], '\n'+section['script'], '\nJob: '+section['job_id']]
        script_text += ['- '+s for s in section.get('sources', [])]
    script_text += ['\n## Lesson sources'] + ['- '+s for s in project.get('sources', [])]
    (build / 'narration.md').write_text('\n'.join(script_text)+'\n', encoding='utf-8')
    manifest = dict(project, schema_version=1, resolution=[width,height], fps=fps, sections=sections,
                    scenes=scenes, duration=duration, captions=captions, build_dir=str(build),
                    narration_duration=sum(s['duration'] for s in sections), codec_tail_padding_seconds=tail_guard, project_path=str(project_path))
    write(build / 'manifest.json', manifest)
    return {'manifest':str(build / 'manifest.json'), 'duration':duration, 'sections':len(sections), 'scenes':len(scenes)}


def encode(manifest_path, states_path, output):
    from PIL import Image
    m = read(manifest_path)
    build = Path(m['build_dir'])
    output = Path(output).resolve()
    require(not output.exists(), 'Refuse to overwrite an encoded revision')
    output.parent.mkdir(parents=True, exist_ok=True)
    states_base = Path(states_path).resolve().parent
    states = read(states_path)
    by_frame = {}
    fps = m['fps']
    for state in states:
        require(0 <= state['time'] < m['duration'], 'Visual state outside video timeline')
        state = dict(state, path=str(resolve(states_base, state['path'])))
        by_frame[math.ceil(state['time']*fps-1e-6)] = state
    ordered = sorted(by_frame.items())
    require(ordered and ordered[0][0] == 0, 'Visual states must start at frame zero')
    require({s['id'] for s in m['scenes']} <= {s['scene'] for _,s in ordered}, 'Some scenes have no render states')
    frames_dir = build / ('encode-'+output.stem)
    require(not frames_dir.exists(), 'Use a fresh output/build revision')
    frames_dir.mkdir()
    events = []
    lines = ['ffconcat version 1.0']
    def entry(path, frames):
        if frames > 0:
            require("'" not in str(path) and '\n' not in str(path), 'Use an apostrophe-free build path')
            lines.extend(["file '"+str(path)+"'", f'duration {frames/fps:.9f}'])
    total = math.ceil(m['duration']*fps)
    previous = None
    for index, (frame, state) in enumerate(ordered):
        with Image.open(state['path']) as source:
            require(list(source.size) == m['resolution'], 'Wrong render dimensions')
            current = source.convert('RGB')
        final = frames_dir / f'state-{index:04}.png'
        current.save(final)
        end = ordered[index+1][0] if index+1 < len(ordered) else total
        n = min(round(float(m.get('transition_seconds', .24))*fps), end-frame) if previous is not None else 0
        for j in range(n):
            blend = frames_dir / f'transition-{index:04}-{j:02}.png'
            Image.blend(previous, current, (j+1)/n).save(blend)
            entry(blend, 1)
        entry(final, end-frame-n)
        events.append(dict(state, encoded_frame=frame, encoded_time=frame/fps, onset_delay=frame/fps-state['time'], transition_seconds=n/fps))
        previous = current
    lines.append("file '"+str(final)+"'")
    schedule = frames_dir / 'video.ffconcat'
    schedule.write_text('\n'.join(lines)+'\n')
    metadata = frames_dir / 'chapters.txt'
    meta = [';FFMETADATA1']
    for i,section in enumerate(m['sections']):
        end = m['sections'][i+1]['start'] if i+1 < len(m['sections']) else section['start']+section['duration']
        title = re.sub(r'[\r\n=;#\\]', ' ', section['id'])
        meta += ['[CHAPTER]','TIMEBASE=1/1000', f'START={round(section["start"]*1000)}', f'END={round(end*1000)}', 'title='+title]
    metadata.write_text('\n'.join(meta)+'\n')
    # Encode narration independently so a visual/subtitle EOF cannot drop audio-tail samples.
    encoded_audio = frames_dir / 'narration.m4a'
    run(['ffmpeg','-y','-v','error','-i',build/'master.wav','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-ar','48000','-c:a','aac','-b:a','160k',encoded_audio])
    run(['ffmpeg','-y','-v','error','-safe','0','-f','concat','-i',schedule,'-i',encoded_audio,'-i',build/'captions.srt','-f','ffmetadata','-i',metadata,
         '-map','0:v:0','-map','1:a:0','-map','2:s:0','-map_metadata','3','-map_chapters','3','-vf',f'fps={fps},format=yuv420p',
         '-c:v','libx264','-preset','fast','-crf','18','-tune','stillimage','-threads','4',
         '-c:a','copy',
         '-c:s','mov_text','-metadata:s:s:0','language='+m.get('caption_language','eng'),'-disposition:s:0','0','-movflags','+faststart','-t',str(total/fps),output])
    require(output.is_file() and output.stat().st_size > 0, 'Encoder produced no file bytes')
    run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',output])
    record = frames_dir / 'encoded-events.json'
    write(record, events)
    return {'video':str(output),'events':str(record),'duration':total/fps,'states':len(events)}


def verify(manifest_path, events_path, video, pptx=None):
    import numpy as np
    from PIL import Image, ImageDraw
    m = read(manifest_path)
    events = read(events_path)
    video = Path(video).resolve()
    qa = video.parent / (video.stem+'-qa')
    qa.mkdir(exist_ok=True)
    probe = json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',video]))
    vs = next(s for s in probe['streams'] if s['codec_type']=='video')
    audio = next(s for s in probe['streams'] if s['codec_type']=='audio')
    require(vs['codec_name']=='h264' and [vs['width'],vs['height']]==m['resolution'], 'Video codec/dimensions mismatch')
    require(audio['codec_name']=='aac', 'AAC audio stream missing')
    require(abs(float(probe['format']['duration'])-math.ceil(m['duration']*m['fps'])/m['fps']) < .06, 'Video duration mismatch')
    require(any(s['codec_type']=='subtitle' for s in probe['streams']), 'Subtitle track missing')
    run(['ffmpeg','-v','error','-i',video,'-map','0:v','-map','0:a','-f','null','-'])
    decoded = np.frombuffer(run(['ffmpeg','-v','error','-i',video,'-map','0:a:0','-ac','1','-ar','24000','-f','f32le','-']),dtype='<f4')
    audio_checks=[]
    for section in m['sections']:
        pcm, duration = inspect_wav(section['wav'])
        ref=np.frombuffer(pcm,dtype='<i2').astype(float)/32768
        start=round(section['start']*24000)
        got=decoded[start:start+len(ref)].astype(float)
        require(len(got)==len(ref), 'Narration is truncated: '+section['id'])
        corr=float(np.corrcoef(ref,got)[0,1])
        rms=float(np.sqrt(np.mean(got**2)))
        require(math.isfinite(corr) and corr>.97 and rms>.01, 'Narration/source mismatch: '+section['id'])
        audio_checks.append({'section':section['id'],'duration':duration,'correlation':corr,'rms_dbfs':20*math.log10(rms)})
    def frame(t):
        data=run(['ffmpeg','-v','error','-ss',f'{t:.6f}','-i',video,'-frames:v','1','-f','image2pipe','-c:v','png','-'])
        return Image.open(io.BytesIO(data)).convert('RGB')
    scene_checks=[]
    for scene in m['scenes']:
        selected=[e for e in events if e['scene']==scene['id']]
        require(selected, 'Scene absent: '+scene['id'])
        last=selected[-1]
        t=min(scene['end']-.04,last['encoded_time']+last['transition_seconds']+.08)
        require(t>=last['encoded_time'], 'Scene too brief to inspect')
        got=frame(t)
        ref=Image.open(last['path']).convert('RGB')
        mae=float(np.mean(abs(np.asarray(got,dtype=float)-np.asarray(ref,dtype=float))))
        require(mae<3, 'Encoded scene mismatch: '+scene['id'])
        got.save(qa/(scene['id']+'.png'))
        scene_checks.append({'scene':scene['id'],'time':t,'mae':mae})
    event_checks=[]
    for i,event in enumerate(events):
        end=events[i+1]['encoded_time'] if i+1<len(events) else m['duration']
        t=event['encoded_time']+event['transition_seconds']+.04
        if t>=end:continue
        got=np.asarray(frame(t).resize((480,270)),dtype=float)
        ref=np.asarray(Image.open(event['path']).convert('RGB').resize((480,270)),dtype=float)
        mae=float(np.mean(abs(got-ref)))
        require(mae<3, 'Encoded visual cue mismatch')
        event_checks.append({'scene':event['scene'],'time':event['encoded_time'],'mae':mae})
    checkpoints=[]
    for n,section in enumerate(m['sections']):
        sheet=Image.new('RGB',(1440,300),'white')
        for j,(label,t) in enumerate([('beginning',section['start']+min(1,section['duration']/4)),('middle',section['start']+section['duration']/2),('end',section['start']+max(0,section['duration']-.5))]):
            im=frame(t)
            im.save(qa/f'section-{n+1}-{label}.png')
            im.thumbnail((480,270));sheet.paste(im,(j*480,0))
            ImageDraw.Draw(sheet).text((j*480+8,278),f'{label}: {t:.2f}s',fill='black')
            checkpoints.append({'section':section['id'],'position':label,'time':t})
        sheet.save(qa/f'section-{n+1}-review.jpg')
    caption_path=qa/'embedded.srt'
    run(['ffmpeg','-y','-v','error','-i',video,'-map','0:s:0',caption_path])
    pattern=r'\d\d:\d\d:\d\d,\d{3} --> \d\d:\d\d:\d\d,\d{3}'
    original=(Path(m['build_dir'])/'captions.srt').read_text()
    require(re.findall(pattern,original)==re.findall(pattern,caption_path.read_text()), 'Encoded subtitle timestamps differ')
    if pptx:
        import zipfile
        with zipfile.ZipFile(pptx) as z:
            slides=[p for p in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',p)]
            notes=[p for p in z.namelist() if re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml',p)]
            require(len(slides)==len(m['scenes']) and len(notes)==len(slides),'PPTX slides/notes mismatch')
    max_hold=max((events[i+1]['encoded_time'] if i+1<len(events) else m['duration'])-e['encoded_time'] for i,e in enumerate(events))
    report=dict(status='automated_checks_passed_visual_review_required',video=str(video),sha256=digest(video),
                duration=float(probe['format']['duration']),audio_checks=audio_checks,scenes=scene_checks,
                visual_events_checked=event_checks,checkpoints=checkpoints,max_unchanged_visual_seconds=max_hold,
                max_onset_delay=max(e['onset_delay'] for e in events),probe=probe)
    write(qa/'verification.json',report)
    return {'report':str(qa/'verification.json'),'status':report['status'],'scenes':len(scene_checks),'audio_sections':len(audio_checks)}


def preflight():
    checks={name:shutil.which(name) for name in ('ffmpeg','ffprobe','curl','node')}
    checks.update({name:importlib.util.find_spec(name) is not None for name in ('PIL','numpy')})
    required=all(checks[name] for name in ('ffmpeg','ffprobe','PIL','numpy'))
    return dict(local_media_tools_ready=required,checks=checks,
                agent_checks_required=['Authorized Invocal MCP connection','Research access','Editable slide authoring and PNG renderer','Font availability','Persistent output delivery'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('preflight')
    p=sub.add_parser('prepare');p.add_argument('project');p.add_argument('--build',required=True)
    p=sub.add_parser('encode');p.add_argument('manifest');p.add_argument('--states',required=True);p.add_argument('--output',required=True)
    p=sub.add_parser('verify');p.add_argument('manifest');p.add_argument('--events',required=True);p.add_argument('--video',required=True);p.add_argument('--pptx')
    args=parser.parse_args()
    try:
        if args.command=='preflight':result=preflight()
        elif args.command=='prepare':result=prepare(args.project,args.build)
        elif args.command=='encode':result=encode(args.manifest,args.states,args.output)
        else:result=verify(args.manifest,args.events,args.video,args.pptx)
        print(json.dumps(result,indent=2))
        if args.command=='preflight' and not result['local_media_tools_ready']:sys.exit(2)
    except Exception as error:
        print(json.dumps({'status':'failed','error':str(error)},indent=2),file=sys.stderr)
        sys.exit(1)

if __name__=='__main__':main()
