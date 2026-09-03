#target aftereffects
#targetengine "UniverseChineseAssistant"

(function (thisObj) {
    var effects = [
  {
    "category": "发光",
    "cn": "微光",
    "en": "uni.Glimmer",
    "match": "Universe_Glow_Glimmer"
  },
  {
    "category": "发光",
    "cn": "点缩放",
    "en": "uni.Point Zoom",
    "match": "Universe_Glow_Point_Zoom"
  },
  {
    "category": "发光",
    "cn": "色彩辉光",
    "en": "uni.Chromatic Glow",
    "match": "Universe_Glow_Chromatic_Glow"
  },
  {
    "category": "发光",
    "cn": "辉光",
    "en": "uni.Glo Fi",
    "match": "Universe_Glow_Glo_Fi_Premium"
  },
  {
    "category": "发光",
    "cn": "辉光",
    "en": "uni.Glow",
    "match": "Universe_Glow_Glow"
  },
  {
    "category": "发光",
    "cn": "边缘辉光",
    "en": "uni.Edge Glow",
    "match": "Universe_Glow_Edge_Glow_Premium"
  },
  {
    "category": "发光",
    "cn": "量子",
    "en": "uni.Quantum",
    "match": "RG_UNI_Glow_Quantum"
  },
  {
    "category": "发生器",
    "cn": "光谱",
    "en": "uni.Spectralicious",
    "match": "Universe_Generators_Spectralicious"
  },
  {
    "category": "发生器",
    "cn": "分形背景",
    "en": "uni.Fractal Background",
    "match": "Universe_Generators_Fractal_Background"
  },
  {
    "category": "发生器",
    "cn": "柔和渐变背景",
    "en": "uni.Soft Gradient Background",
    "match": "Universe_Generators_Soft_Gradient_Background"
  },
  {
    "category": "发生器",
    "cn": "渐变坡道",
    "en": "uni.Gradient Ramp",
    "match": "Universe_Generators_Gradient_Ramp"
  },
  {
    "category": "发生器",
    "cn": "湍流噪波",
    "en": "uni.Turbulence Noise",
    "match": "Universe_Generators_TurNoise"
  },
  {
    "category": "字幕",
    "cn": "AV视频",
    "en": "uni.AV Club",
    "match": "Universe_Text_AV_Club"
  },
  {
    "category": "字幕",
    "cn": "光泽",
    "en": "uni.Luster",
    "match": "Universe_Text_Luster"
  },
  {
    "category": "字幕",
    "cn": "屏幕文本",
    "en": "uni.Screen Text",
    "match": "Universe_Text_Screen_Text"
  },
  {
    "category": "字幕",
    "cn": "打字开",
    "en": "uni.Type On",
    "match": "Universe_Text_Type_On"
  },
  {
    "category": "字幕",
    "cn": "打字投射",
    "en": "uni.Type Cast",
    "match": "Universe_Text_Type_Cast"
  },
  {
    "category": "字幕",
    "cn": "排版",
    "en": "uni.Typographic",
    "match": "RG_UNI_Text_Typographic"
  },
  {
    "category": "字幕",
    "cn": "数字",
    "en": "uni.Numbers",
    "match": "Universe_Text_Numbers"
  },
  {
    "category": "字幕",
    "cn": "文本平铺",
    "en": "uni.Text Tile",
    "match": "Universe_Text_Text_Tile"
  },
  {
    "category": "字幕",
    "cn": "标题运动",
    "en": "uni.Title Motion",
    "match": "Universe_Utilities_Title_Motion"
  },
  {
    "category": "字幕",
    "cn": "辉光II",
    "en": "uni.Glo Fi II",
    "match": "Universe_Text_Glo_Fi_II"
  },
  {
    "category": "字幕",
    "cn": "长阴影",
    "en": "uni.Long Shadow",
    "match": "Universe_Text_Long_Shadow"
  },
  {
    "category": "字幕",
    "cn": "霓虹",
    "en": "uni.Ecto",
    "match": "Universe_Text_Ecto"
  },
  {
    "category": "字幕",
    "cn": "黑客文本",
    "en": "uni.Hacker Text",
    "match": "Universe_Text_Hacker_Text"
  },
  {
    "category": "实用程序",
    "cn": "去乘",
    "en": "uni.Unmult",
    "match": "Universe_Utilities_Unmult_Premium"
  },
  {
    "category": "实用程序",
    "cn": "徽标运动",
    "en": "uni.Logo Motion",
    "match": "Universe_Utilities_Logo_Motion"
  },
  {
    "category": "实用程序",
    "cn": "模式",
    "en": "uni.Modes",
    "match": "RG_UNI_Utilities_Modes"
  },
  {
    "category": "实用程序",
    "cn": "社交",
    "en": "uni.Socialize",
    "match": "RG_UNI_Utilities_Socialize"
  },
  {
    "category": "扭曲",
    "cn": "分离",
    "en": "uni.RGB Separation",
    "match": "Universe_Distort_RGB_Separation"
  },
  {
    "category": "扭曲",
    "cn": "棱镜置换",
    "en": "uni.Prism Displacement",
    "match": "Universe_Distort_Prism_Displacement"
  },
  {
    "category": "扭曲",
    "cn": "热浪",
    "en": "uni.Heatwave",
    "match": "Universe_Distort_Heatwave"
  },
  {
    "category": "扭曲",
    "cn": "画中画",
    "en": "uni.Picture in Picture",
    "match": "Universe_Distort_Picture_in_Picture"
  },
  {
    "category": "扭曲",
    "cn": "相机抖动",
    "en": "uni.Camera Shake",
    "match": "Universe_Distort_Camera_Shake_Pro"
  },
  {
    "category": "扭曲",
    "cn": "色彩像差",
    "en": "uni.Chromatic Aberration",
    "match": "Universe_Distort_Chromatic_Aberration"
  },
  {
    "category": "模糊",
    "cn": "复合模糊",
    "en": "uni.Compound Blur",
    "match": "Universe_Compound_Blur_Premium"
  },
  {
    "category": "模糊",
    "cn": "模糊",
    "en": "uni.Blur",
    "match": "Universe_Blur_Blur_Premium"
  },
  {
    "category": "模糊",
    "cn": "盒散景",
    "en": "uni.Box Bokeh",
    "match": "Universe_Blur_Box_Bokeh"
  },
  {
    "category": "模糊",
    "cn": "聚光模糊",
    "en": "uni.Spot Blur",
    "match": "Universe_Blur_Spot_Blur"
  },
  {
    "category": "转场",
    "cn": "三角波浪",
    "en": "uni.Triangle Wave",
    "match": "Universe_Transitions_Triangle_Wave"
  },
  {
    "category": "转场",
    "cn": "光谱转场",
    "en": "uni.Spectralicious Transition",
    "match": "Universe_Transitions_Spectralicious_Transition"
  },
  {
    "category": "转场",
    "cn": "内部立方体",
    "en": "uni.Inside Cube",
    "match": "Universe_Transitions_Inside_Cube"
  },
  {
    "category": "转场",
    "cn": "半灯光",
    "en": "uni.HalfLight",
    "match": "Universe_Transitions_HalfLight"
  },
  {
    "category": "转场",
    "cn": "复古转场",
    "en": "uni.RetroGrade Transition",
    "match": "Universe_Transitions_RetroGrade_Transition"
  },
  {
    "category": "转场",
    "cn": "展开",
    "en": "uni.Unfold",
    "match": "Universe_Transitions_Unfold"
  },
  {
    "category": "转场",
    "cn": "形状擦除",
    "en": "uni.Shape Wipe",
    "match": "Universe_Transitions_Shape_Wipe"
  },
  {
    "category": "转场",
    "cn": "扫过平移",
    "en": "uni.Swish Pan",
    "match": "Universe_Swish_Pan_Premium"
  },
  {
    "category": "转场",
    "cn": "扭曲",
    "en": "uni.Warp",
    "match": "RG_UNI_Transition_Warp"
  },
  {
    "category": "转场",
    "cn": "折叠",
    "en": "uni.Fold",
    "match": "Universe_Transitions_Fold"
  },
  {
    "category": "转场",
    "cn": "拉伸",
    "en": "uni.Stretch",
    "match": "RG_UNI_Transition_Stretch"
  },
  {
    "category": "转场",
    "cn": "推轨淡化",
    "en": "uni.Dolly Fade",
    "match": "Universe_Transitions_Dolly_Fade"
  },
  {
    "category": "转场",
    "cn": "故障转场",
    "en": "uni.Glitch Transition",
    "match": "Universe_Transitions_Glitch_Transition"
  },
  {
    "category": "转场",
    "cn": "旋转木马转场",
    "en": "uni.Carousel Transition",
    "match": "Universe_Transitions_Carousel_Transition"
  },
  {
    "category": "转场",
    "cn": "时钟擦除",
    "en": "uni.Clock Wipe",
    "match": "Universe_Transitions_Clock_Wipe"
  },
  {
    "category": "转场",
    "cn": "曝光模糊",
    "en": "uni.Exposure Blur",
    "match": "Universe_Exposure_Blur_Premium"
  },
  {
    "category": "转场",
    "cn": "柔和边缘擦除",
    "en": "uni.Soft Edge Wipe",
    "match": "Universe_Soft_Edge_Wipe_Premium"
  },
  {
    "category": "转场",
    "cn": "湍流转场",
    "en": "uni.Turbulence Transition",
    "match": "Universe_Transitions_Turbulence_Transition"
  },
  {
    "category": "转场",
    "cn": "滑动",
    "en": "uni.Slide",
    "match": "Universe_Transitions_Slide"
  },
  {
    "category": "转场",
    "cn": "百叶窗",
    "en": "uni.Blinds",
    "match": "Universe_Transitions_Blinds"
  },
  {
    "category": "转场",
    "cn": "相机抖动转场",
    "en": "uni.Camera Shake Transition",
    "match": "Universe_Transitions_Camera_Shake_Transition"
  },
  {
    "category": "转场",
    "cn": "立方体",
    "en": "uni.Cube",
    "match": "Universe_Transitions_Cube"
  },
  {
    "category": "转场",
    "cn": "线性擦除",
    "en": "uni.Linear Wipe",
    "match": "Universe_Transitions_Linear_Wipe"
  },
  {
    "category": "转场",
    "cn": "胶片转场",
    "en": "uni.Film Transition",
    "match": "Universe_Transitions_Film_Transition"
  },
  {
    "category": "转场",
    "cn": "菱形波浪",
    "en": "uni.Diamond Wave",
    "match": "Universe_Transitions_Diamond_Wave"
  },
  {
    "category": "转场",
    "cn": "诺尔灯光转场",
    "en": "uni.Knoll Light Transition",
    "match": "Universe_Transitions_Knoll_Light_Transition"
  },
  {
    "category": "转场",
    "cn": "转场",
    "en": "uni.VHS Transition",
    "match": "Universe_Transitions_VHS_Transition"
  },
  {
    "category": "转场",
    "cn": "通道冲浪",
    "en": "uni.Channel Surf",
    "match": "Universe_Transitions_Channel_Surf"
  },
  {
    "category": "转场",
    "cn": "通道模糊",
    "en": "uni.Channel Blur",
    "match": "Universe_Transitions_Channel_Blur"
  },
  {
    "category": "转场",
    "cn": "闪烁切换",
    "en": "uni.Flicker Cut",
    "match": "Universe_Transitions_Flicker_Cut"
  },
  {
    "category": "转场",
    "cn": "颜色条纹",
    "en": "uni.Color Stripe",
    "match": "Universe_Transitions_Color_Stripe"
  },
  {
    "category": "转场",
    "cn": "颜色马赛克转场",
    "en": "uni.Color Mosaic Transition",
    "match": "Universe_Transitions_Color_Mosaic"
  },
  {
    "category": "转场",
    "cn": "魔方立方体",
    "en": "uni.Rubix Cube",
    "match": "Universe_Transitions_Rubics_Cube"
  },
  {
    "category": "运动图形",
    "cn": "线",
    "en": "uni.Line",
    "match": "Universe_Motion_Graphics_Draw_Path"
  },
  {
    "category": "运动图形",
    "cn": "组件",
    "en": "uni.HUD Components",
    "match": "Universe_Visualizations_HUD_Components"
  },
  {
    "category": "运动图形",
    "cn": "进度",
    "en": "uni.Progresso",
    "match": "Universe_M_G_Progresso"
  },
  {
    "category": "运动图形",
    "cn": "重构",
    "en": "uni.Reframe",
    "match": "RG_UNI_M_G_Reframe"
  },
  {
    "category": "运动图形",
    "cn": "阵列枪",
    "en": "uni.Array Gun",
    "match": "Universe_M_G_Array_Gun"
  },
  {
    "category": "风格化",
    "cn": "全息矩阵II",
    "en": "uni.Holomatrix II",
    "match": "Universe_Distort_Holomatrix"
  },
  {
    "category": "风格化",
    "cn": "动态纹理化",
    "en": "uni.Texturize Motion",
    "match": "MX_UNI_Stylize_Texturize_Motion"
  },
  {
    "category": "风格化",
    "cn": "复古",
    "en": "uni.RetroGrade",
    "match": "Universe_CrumplePop_RetroGrade"
  },
  {
    "category": "风格化",
    "cn": "多色调",
    "en": "uni.Multitone",
    "match": "RG_UNI_Stylize_Multitone"
  },
  {
    "category": "风格化",
    "cn": "失火",
    "en": "uni.MisFire",
    "match": "Universe_Misfire_Premium"
  },
  {
    "category": "风格化",
    "cn": "收缩光线",
    "en": "uni.ShrinkRay",
    "match": "Universe_CrumplePop_ShrinkRay"
  },
  {
    "category": "风格化",
    "cn": "故障",
    "en": "uni.Glitch",
    "match": "Universe_Stylize_Glitch"
  },
  {
    "category": "风格化",
    "cn": "旋转木马",
    "en": "uni.Carousel",
    "match": "Universe_Stylize_Carousel"
  },
  {
    "category": "风格化",
    "cn": "模拟",
    "en": "uni.Analog",
    "match": "RG_UNI_Stylize_Analog"
  },
  {
    "category": "风格化",
    "cn": "电气",
    "en": "uni.Electrify",
    "match": "RG_UNI_Stylize_Electrify"
  },
  {
    "category": "风格化",
    "cn": "符号映射",
    "en": "uni.Symbol Mapper",
    "match": "Universe_Stylize_Symbol_Mapper"
  },
  {
    "category": "风格化",
    "cn": "精修",
    "en": "uni.Finisher",
    "match": "Universe_CrumplePop_Finisher"
  },
  {
    "category": "风格化",
    "cn": "素描化",
    "en": "uni.Sketchify",
    "match": "Universe_Stylize_Sketchify"
  },
  {
    "category": "风格化",
    "cn": "纹理化",
    "en": "uni.Texturize",
    "match": "Universe_Stylize_Texturize"
  },
  {
    "category": "风格化",
    "cn": "色彩城",
    "en": "uni.ChromaTown",
    "match": "RG_UNI_Chromatown"
  },
  {
    "category": "风格化",
    "cn": "诺尔光厂EZ",
    "en": "uni.Knoll Light Factory EZ",
    "match": "Universe_Knoll_Light_Factory_EZ"
  },
  {
    "category": "风格化",
    "cn": "过曝光",
    "en": "uni.OverLight",
    "match": "Universe_CrumplePop_OverLight"
  },
  {
    "category": "风格化",
    "cn": "颗粒16",
    "en": "uni.Grain16",
    "match": "Universe_CrumplePop_Grain16"
  },
  {
    "category": "风格化",
    "cn": "鱼眼修复",
    "en": "uni.Fisheye Fixer",
    "match": "Universe_CrumplePop_Fisheye_Fixer"
  },
  {
    "category": "风格化",
    "cn": "黑白",
    "en": "uni.Noir",
    "match": "Universe_Stylize_Noir_Moderne"
  }
];
    var visible = [];
    function buildUI(host) {
        var panel = (host instanceof Panel) ? host : new Window("palette", "宇宙插件中文助手", undefined, {resizeable:true});
        panel.orientation = "column"; panel.alignChildren = ["fill", "top"]; panel.margins = 12;
        var search = panel.add("edittext", undefined, ""); search.characters = 36; search.helpTip = "按中文、英文或分类搜索";
        var group = panel.add("dropdownlist", undefined, ["全部"]);
        var categories = {}; var i;
        for (i=0; i<effects.length; i++) categories[effects[i].category] = true;
        for (var key in categories) group.add("item", key);
        group.selection = 0;
        var list = panel.add("listbox", undefined, [], {multiselect:false}); list.preferredSize = [530, 380];
        var status = panel.add("statictext", undefined, "选择中文效果后，添加到当前合成的所有选中图层。", {multiline:true});
        var add = panel.add("button", undefined, "添加效果");
        function rebuild() {
            var q = search.text.toLowerCase(), cat = group.selection ? group.selection.text : "全部";
            visible = []; list.removeAll();
            for (var j=0; j<effects.length; j++) {
                var e=effects[j], text=e.category+" · "+e.cn+"  ["+e.en+"]";
                if ((cat==="全部" || e.category===cat) && (q==="" || text.toLowerCase().indexOf(q)!==-1)) {
                    visible.push(e); list.add("item", text);
                }
            }
            if (list.items.length) list.selection=0;
        }
        search.onChanging=rebuild; group.onChange=rebuild;
        add.onClick=function () {
            if (!list.selection) { alert("请先选择效果。"); return; }
            var comp=app.project.activeItem;
            if (!(comp instanceof CompItem)) { alert("请先打开一个合成。"); return; }
            var layers=comp.selectedLayers;
            if (!layers || layers.length===0) { alert("请先选择一个或多个图层。"); return; }
            var e=visible[list.selection.index], ok=0, failed=[];
            app.beginUndoGroup("宇宙插件中文助手：添加效果");
            try {
                for (var k=0; k<layers.length; k++) {
                    try { var fx=layers[k].property("ADBE Effect Parade").addProperty(e.match); if (fx) ok++; else failed.push(layers[k].name); }
                    catch(err) { failed.push(layers[k].name); }
                }
            } finally { app.endUndoGroup(); }
            status.text = ok>0 ? "已添加："+e.cn+"（"+e.en+"），图层数："+ok : "添加失败："+e.en+"。";
            if (failed.length) alert("部分图层未能添加："+failed.join(", "));
        };
        panel.onResizing=panel.onResize=function(){this.layout.resize();}; rebuild(); panel.layout.layout(true); return panel;
    }
    var ui=buildUI(thisObj); if (ui instanceof Window) {ui.center();ui.show();}
})(this);
