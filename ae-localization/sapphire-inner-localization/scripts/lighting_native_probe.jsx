// Template only. Generate with prepare_lighting_probe.py before running in AE.
(function () {
    var cfg = /*__LIGHTING_CONFIG__*/;
    if (!app.project || app.project.numItems !== 0 || app.project.file) throw new Error('Refuse existing user project');
    var root = new Folder(cfg.work_dir);
    if (!root.exists && !root.create()) throw new Error('Cannot create diagnostic directory');
    var output = new File(root.fsName + '/' + cfg.tag + '.aep');
    if (output.exists) throw new Error('Refuse existing diagnostic project');
    var frames = new Folder(root.fsName + '/frames');
    if (!frames.exists && !frames.create()) throw new Error('Cannot create frame directory');
    var log = app.project.items.addFolder('LIGHTING DIAGNOSTIC');
    log.comment = 'LIGHTING_PROBE ' + cfg.tag;
    app.project.save(output); // Before any menu/UI operation, bind the owned project.
    app.exitAfterLaunchAndEval = true;
    function owned() { return app.project && app.project.file && app.project.file.fsName === output.fsName; }
    function guard() {
        if (!owned()) { app.exitAfterLaunchAndEval = false; throw new Error('User project changed; no further actions'); }
    }
    function save() { guard(); app.project.save(output); }
    try {
        var names = {}, counts = {}, commands = {}, i, j, id;
        for (i = 0; i < cfg.cases.length; i++) for (j = 0; j < cfg.cases[i].effects.length; j++) counts[cfg.cases[i].effects[j]] = 0;
        for (i = 0; i < app.effects.length; i++) {
            var registered = app.effects[i];
            if (counts[registered.matchName] !== undefined) { counts[registered.matchName]++; names[registered.matchName] = registered.displayName; }
        }
        // Cache before any insertion: later same-name lookup can return Repeat Last Effect.
        for (id in counts) if (counts.hasOwnProperty(id)) {
            if (counts[id] !== 1) throw new Error('Effect identity not unique: ' + id);
            commands[id] = app.findMenuCommandId(names[id]);
            if (commands[id] === 0 || commands[id] === 2452) throw new Error('Effect command missing or Repeat command: ' + id);
        }
        var media = new File(cfg.media_path);
        if (!media.exists) throw new Error('Fixture media missing');
        guard(); var footage = app.project.importFile(new ImportOptions(media));
        var duration = cfg.time_seconds + cfg.span_frames / cfg.fps + 1;
        if (footage.duration < duration) throw new Error('Fixture is too short');
        var total = 0;
        for (i = 0; i < cfg.cases.length; i++) {
            guard(); var current = cfg.cases[i];
            var c = app.project.items.addComp(current.name, footage.width, footage.height, footage.pixelAspect, duration, cfg.fps);
            var layer = c.layers.add(footage); c.time = cfg.time_seconds;
            c.resolutionFactor = [cfg.resolution_divisor, cfg.resolution_divisor];
            var viewer = c.openInViewer();
            for (j = 0; j < current.effects.length; j++) {
                guard(); viewer.setActive(); layer.selected = true; id = current.effects[j];
                log.comment += '\nADDING ' + current.name + ' ' + id + ' COMMAND ' + commands[id]; save();
                app.executeCommand(commands[id]); guard();
                var parade = layer.property('ADBE Effect Parade');
                if (parade.numProperties !== j + 1) throw new Error('Wrong effect count');
                for (var k = 0; k <= j; k++) if (parade.property(k + 1).matchName !== current.effects[k]) throw new Error('Wrong effect identity/order');
                total++; log.comment += '\nADDED ' + current.name + ' ' + id; save();
            }
            // Read after all insertions; do not retain property handles across add operations.
            for (j = 0; j < current.effects.length; j++) {
                var effect = layer.property('ADBE Effect Parade').property(j + 1);
                var label = current.name + '__' + (j + 1) + '__' + current.effects[j];
                var rows = ['REPAIR_BEGIN ' + label];
                for (var n = 1; n <= effect.numProperties; n++) {
                    var parameter = effect.property(n), value = 'SKIPPED';
                    if (parameter.propertyType === PropertyType.PROPERTY && parameter.propertyValueType !== PropertyValueType.CUSTOM_VALUE && parameter.propertyValueType !== PropertyValueType.NO_VALUE) value = String(parameter.value);
                    rows.push(n + '|' + parameter.name + '|' + parameter.matchName + '|' + parameter.propertyType + '|' + value);
                }
                rows.push('REPAIR_END ' + label); var note = app.project.items.addFolder('CHECK ' + label); note.comment = rows.join('\n');
            }
            guard(); var queue = app.project.renderQueue.items.add(c);
            queue.timeSpanStart = cfg.time_seconds; queue.timeSpanDuration = cfg.span_frames / cfg.fps;
            var om = queue.outputModule(1), templates = om.templates, found = false;
            for (j = 0; j < templates.length; j++) if (/TIFF/i.test(templates[j])) { om.applyTemplate(templates[j]); found = true; break; }
            if (!found) throw new Error('No verified TIFF template');
            om.file = new File(frames.fsName + '/' + current.name + '_[#####].tif'); save();
        }
        guard(); log.comment += '\nALL_ADDED ' + total; save(); guard(); app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
    } catch (error) {
        if (!owned()) { app.exitAfterLaunchAndEval = false; return; }
        log.comment += '\nPROBE_ERROR ' + error.toString() + ' LINE ' + error.line;
        save(); guard(); app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
    }
})();
