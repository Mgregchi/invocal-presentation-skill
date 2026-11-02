import importlib.util, unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'plugins/invocal-presentation-skill/skills/invocal-presentation/scripts/render_motion.py'
s=importlib.util.spec_from_file_location('motion',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class MotionTests(unittest.TestCase):
 def chart(self):return dict(kind='bar',values=[4,7],labels=['A','B'],domain=[0,10],ticks=[0,5,10],reveals=[1,2],source='Synthetic test data')
 def test_easing_never_overshoots(self):
  for easing in ['linear','smooth']:
   values=[m.progress(t/100,1,1,easing) for t in range(301)]
   self.assertEqual(values,sorted(values));self.assertEqual(values[0],0);self.assertEqual(values[-1],1)
 def test_zero_baseline_required(self):
  c=self.chart();c['domain']=[2,10]
  with self.assertRaises(ValueError):m.validate_chart(c)
 def test_invalid_data_rejected(self):
  for values in ([float('nan'),7],[4,11]):
   c=self.chart();c['values']=values
   with self.assertRaises(ValueError):m.validate_chart(c)
 def test_line_cues_cannot_collide(self):
  c=self.chart();c.update(kind='line',reveals=[1,1])
  with self.assertRaises(ValueError):m.validate_chart(c)
 def test_missing_source_rejected(self):
  c=self.chart();del c['source']
  with self.assertRaises(ValueError):m.validate_chart(c)
 def test_legitimate_chart(self):m.validate_chart(self.chart())
if __name__=='__main__':unittest.main()
