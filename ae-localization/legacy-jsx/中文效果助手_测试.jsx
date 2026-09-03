#target aftereffects
#targetengine "ChineseEffectAssistant"

(function (thisObj) {
    var entries = [
        { cn: "旋转木马转场", en: "uni.Carousel Transition", match: "Universe_Transitions_Carousel_Transition" },
        { cn: "社交", en: "uni.Socialize", match: "Universe_Utilities_Socialize" },
        { cn: "弯曲", en: "CC Bend It", match: "CC Bend It" }
    ];

    function makePanel(host) {
        var panel = (host instanceof Panel) ? host : new Window("palette", "中文效果助手（测试）", undefined, { resizeable: true });
        panel.orientation = "column";
        panel.alignChildren = ["fill", "top"];
        panel.margins = 12;

        var search = panel.add("edittext", undefined, "");
        search.characters = 32;
        search.helpTip = "按中文或英文筛选";
        var list = panel.add("listbox", undefined, [], { multiselect: false });
        list.preferredSize = [430, 155];
        var info = panel.add("statictext", undefined, "选择效果后，添加到当前合成的首个选中图层。", { multiline: true });
        var add = panel.add("button", undefined, "添加效果");

        function render() {
            var query = search.text.toLowerCase();
            list.removeAll();
            for (var i = 0; i < entries.length; i++) {
                var item = entries[i];
                var text = item.cn + "  —  " + item.en;
                if (query === "" || text.toLowerCase().indexOf(query) !== -1) {
                    var row = list.add("item", text);
                    row.entry = item;
                }
            }
            if (list.items.length > 0) list.selection = 0;
        }

        search.onChanging = render;
        add.onClick = function () {
            if (!list.selection) { alert("请先选择效果。"); return; }
            var comp = app.project.activeItem;
            if (!(comp instanceof CompItem)) { alert("请先激活一个合成。"); return; }
            if (comp.selectedLayers.length < 1) { alert("请先选择一个图层。"); return; }
            var selected = list.selection.entry;
            app.beginUndoGroup("中文效果助手：添加效果");
            try {
                var effect = comp.selectedLayers[0].property("ADBE Effect Parade").addProperty(selected.match);
                if (effect === null) throw new Error("宿主未返回效果对象。");
                info.text = "已添加：" + selected.cn + "（" + selected.en + "）";
            } catch (err) {
                info.text = "添加失败：" + selected.en;
                alert("未能添加“" + selected.en + "”。\n" + err.toString());
            } finally {
                app.endUndoGroup();
            }
        };
        panel.onResizing = panel.onResize = function () { this.layout.resize(); };
        render();
        panel.layout.layout(true);
        return panel;
    }

    var ui = makePanel(thisObj);
    if (ui instanceof Window) { ui.center(); ui.show(); }
})(this);
