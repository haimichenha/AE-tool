# -*- coding: utf-8 -*-
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(r"C:\Program Files\Adobe\Common\Plug-ins\7.0\MediaCore")
BASE=Path(r"E:\插件备份\AE_PR_汉化工作\MediaCore_汉化前备份_20260830")
SNAP=Path(r"E:\插件备份\AE_PR_汉化工作\Universe_全中文模式快照_20260830")
WORK=Path(r"E:\插件备份\AE_PR_汉化工作")
PANEL=Path(r"E:\课程文件\四六级\抱回研研舞\中文效果助手.jsx")
PANEL_DEST=Path(r"D:\AZBao\PR 22\Ae2022\Adobe After Effects 2022\Support Files\Scripts\ScriptUI Panels\宇宙插件中文助手.jsx")
FILES=[
 "Red Giant Universe\\Universe_Blur_Blur_Premium_AE_Fx.aex",
 "Red Giant Universe\\Universe_Blur_Box_Bokeh_AE_Fx.aex",
 "Red Giant Universe\\Universe_Blur_Compound_Blur_Premium_AE_Fx.aex",
 "Red Giant Universe\\Universe_Blur_Spot_Blur_AE_Fx.aex",
 "Red Giant Universe\\Universe_CrumplePop_Finisher_AE_Fx.aex",
 "Red Giant Universe\\Universe_CrumplePop_Fisheye_Fixer_AE_Fx.aex",
 "Red Giant Universe\\Universe_CrumplePop_Grain16_AE_Fx.aex",
 "Red Giant Universe\\Universe_CrumplePop_OverLight_AE_Fx.aex",
 "Red Giant Universe\\Universe_CrumplePop_ShrinkRay_AE_Fx.aex",
 "Red Giant Universe\\Universe_Distort_Camera_Shake_Pro_AE_Fx.aex",
 "Red Giant Universe\\Universe_Distort_Chromatic_Aberration_AE_Fx.aex",
 "Red Giant Universe\\Universe_Distort_Heatwave_AE_Fx.aex",
 "Red Giant Universe\\Universe_Distort_Picture_in_Picture_AE_Fx.aex",
 "Red Giant Universe\\Universe_Distort_Prism_Displacement_AE_Fx.aex",
 "Red Giant Universe\\Universe_Distort_RGB_Separation_AE_Fx.aex",
 "Red Giant Universe\\Universe_Generators_Fractal_Background_AE_Fx.aex",
 "Red Giant Universe\\Universe_Generators_Gradient_Ramp_AE_Fx.aex",
 "Red Giant Universe\\Universe_Generators_Soft_Gradient_Background_AE_Fx.aex",
 "Red Giant Universe\\Universe_Generators_Spectralicious_AE_Fx.aex",
 "Red Giant Universe\\Universe_Glow_Chromatic_Glow_AE_Fx.aex",
 "Red Giant Universe\\Universe_Glow_Edge_Glow_Premium_AE_Fx.aex",
 "Red Giant Universe\\Universe_Glow_Glimmer_AE_Fx.aex",
 "Red Giant Universe\\Universe_Glow_Glo_Fi_Premium_AE_Fx.aex",
 "Red Giant Universe\\Universe_Glow_Glow_AE_Fx.aex",
 "Red Giant Universe\\Universe_Glow_Point_Zoom_AE_Fx.aex",
 "Red Giant Universe\\Universe_Glow_Quantum_AE_Fx.aex",
 "Red Giant Universe\\Universe_Motion_Graphics_Array_Gun_AE_Fx.aex",
 "Red Giant Universe\\Universe_Motion_Graphics_HUD_Components_AE_Fx.aex",
 "Red Giant Universe\\Universe_Motion_Graphics_Line_AE_Fx.aex",
 "Red Giant Universe\\Universe_Motion_Graphics_Progresso_AE_Fx.aex",
 "Red Giant Universe\\Universe_Motion_Graphics_Reframe_AE_Fx.aex",
 "Red Giant Universe\\Universe_Noise_Turbulence_Noise_AE_Fx.aex",
 "Red Giant Universe\\Universe_Stylize_Analog_AE_Fx.aex",
 "Red Giant Universe\\Universe_Stylize_Carousel_AE_Fx.aex",
 "Red Giant Universe\\Universe_Stylize_ChromaTown_AE_Fx.aex",
 "Red Giant Universe\\Universe_Stylize_Electrify_AE_Fx.aex",
 "Red Giant Universe\\Universe_Stylize_Glitch_AE_Fx.aex",
 "Red Giant Universe\\Universe_Stylize_Holomatrix_AE_Fx.aex",
 "Red Giant Universe\\Universe_Stylize_Knoll_Light_Factory_EZ_AE_Fx.aex",
 "Red Giant Universe\\Universe_Stylize_Misfire_Premium_AE_Fx.aex",
 "Red Giant Universe\\Universe_Stylize_Multitone_AE_Fx.aex",
 "Red Giant Universe\\Universe_Stylize_Noir_Moderne_AE_Fx.aex",
 "Red Giant Universe\\Universe_Stylize_RetroGrade_AE_Fx.aex",
 "Red Giant Universe\\Universe_Stylize_Sketchify_AE_Fx.aex",
 "Red Giant Universe\\Universe_Stylize_Symbol_Mapper_AE_Fx.aex",
 "Red Giant Universe\\Universe_Stylize_Texturize_AE_Fx.aex",
 "Red Giant Universe\\Universe_Stylize_Texturize_Motion_AE_Fx.aex",
 "Red Giant Universe\\Universe_Text_AV_Club_AE_Fx.aex",
 "Red Giant Universe\\Universe_Text_Ecto_AE_Fx.aex",
 "Red Giant Universe\\Universe_Text_Glo_Fi_II_AE_Fx.aex",
 "Red Giant Universe\\Universe_Text_Hacker_Text_AE_Fx.aex",
 "Red Giant Universe\\Universe_Text_Long_Shadow_AE_Fx.aex",
 "Red Giant Universe\\Universe_Text_Luster_AE_Fx.aex",
 "Red Giant Universe\\Universe_Text_Numbers_AE_Fx.aex",
 "Red Giant Universe\\Universe_Text_Screen_Text_AE_Fx.aex",
 "Red Giant Universe\\Universe_Text_Text_Tile_AE_Fx.aex",
 "Red Giant Universe\\Universe_Text_Title_Motion_AE_Fx.aex",
 "Red Giant Universe\\Universe_Text_Type_Cast_AE_Fx.aex",
 "Red Giant Universe\\Universe_Text_Type_On_AE_Fx.aex",
 "Red Giant Universe\\Universe_Text_Typographic_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Blinds_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Camera_Shake_Transition_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Carousel_Transition_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Channel_Blur_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Channel_Surf_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Clock_Wipe_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Color_Mosaic_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Color_Stripe_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Cube_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Diamond_Wave_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Dolly_Fade_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Exposure_Blur_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Film_Transition_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Flicker_Cut_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Fold_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Glitch_Transition_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_HalfLight_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Inside_Cube_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Knoll_Light_Transition_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Linear_Wipe_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_RetroGrade_Transition_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Rubics_Cube_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Shape_Wipe_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Slide_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Soft_Edge_Wipe_Premium_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Spectralicious_Transition_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Stretch_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Swish_Pan_Premium_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Triangle_Wave_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Turbulence_Transition_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Unfold_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_VHS_Transition_AE_Fx.aex",
 "Red Giant Universe\\Universe_Transitions_Warp_AE_Fx.aex",
 "Red Giant Universe\\Universe_Utilities_Logo_Motion_AE_Fx.aex",
 "Red Giant Universe\\Universe_Utilities_Modes_AE_Fx.aex",
 "Red Giant Universe\\Universe_Utilities_Socialize_AE_Fx.aex",
 "Red Giant Universe\\Universe_Utilities_Unmult_Premium_AE_Fx.aex"
]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args()
 print('Universe functional-mode candidates:',len(FILES))
 for rel in FILES:
  if not (ROOT/rel).is_file() or not (BASE/rel).is_file():raise RuntimeError('missing: '+rel)
 if not PANEL.is_file():raise RuntimeError('panel source missing')
 if not args.apply:return
 rows=[]
 for rel in FILES:
  target=ROOT/rel;baseline=BASE/rel;snap=SNAP/rel;snap.parent.mkdir(parents=True,exist_ok=True)
  current=sha(target)
  if snap.exists():
   if sha(snap)!=current:raise RuntimeError('snapshot collision differs: '+rel)
  else:shutil.copy2(target,snap)
  expected=sha(baseline);shutil.copy2(baseline,target)
  actual=sha(target)
  if actual!=expected:raise RuntimeError('restore mismatch: '+rel)
  rows.append({'file':str(rel),'chinese_sha':current,'functional_sha':actual,'snapshot':str(snap)})
 if PANEL_DEST.exists():
  prior=WORK/'ScriptUI面板备份_20260830'/PANEL_DEST.name;prior.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PANEL_DEST,prior)
 shutil.copy2(PANEL,PANEL_DEST)
 (WORK/'Universe_功能模式_恢复清单_20260830.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 (WORK/'Universe_当前模式.json').write_text(json.dumps({'mode':'functional_original_ids','files':len(rows),'dashboard':'supported','chinese_panel':str(PANEL_DEST)},ensure_ascii=False,indent=2),encoding='utf-8')
 print('Restored functional Universe:',len(rows),'Installed panel:',PANEL_DEST)
if __name__=='__main__':main()
