// Forward-test generated JSX against a minimal host model; never starts Adobe.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const scenario = process.argv[3];
const exists = new Set();
let app, active, calls = 0, lookups = 0, userSaves = 0, userCloses = 0, diagnostic;
const File = function (path) { this.fsName = path; };
Object.defineProperty(File.prototype, 'exists', {get() { return this.fsName.endsWith('.mp4') || exists.has(this.fsName); }});
const Folder = function (path) { this.fsName = path; this.exists = true; this.create = () => true; };
const makeEffect = id => ({matchName: id, numProperties: 2, property(index) {
  return {name: index === 1 ? 'Brightness' : 'Hidden', matchName: `${id}-${index}`,
    propertyType: 1, propertyValueType: index === 1 ? 1 : 3, value: 1};
}});
function makeProject(user = false) {
  const entries = [];
  const project = {
    file: user ? new File('D:/user/unsaved.aep') : null,
    get numItems() { return entries.length + (user ? 1 : 0); },
    save(file) { if (user) userSaves++; this.file = file; exists.add(file.fsName); },
    close() { if (user) userCloses++; this.closed = true; },
    importFile() { return {width: 64, height: 64, pixelAspect: 1, duration: 20}; },
    items: {
      addFolder(name) { const e = {name, comment: ''}; entries.push(e); return e; },
      addComp(name) {
        const effects = [];
        const parade = {get numProperties() {return effects.length;}, property(n) {return effects[n - 1];}};
        const layer = {property() {return parade;}};
        const comp = {name, effects, layers: {add() {return layer;}}, openInViewer() {return {setActive() {active = comp;}};}};
        entries.push(comp); return comp;
      }
    },
    renderQueue: {items: {add() { return {outputModule() {return {templates: ['TIFF'], applyTemplate() {}};}};}}},
    entries
  };
  return project;
}
diagnostic = makeProject(scenario === 'existing');
const user = makeProject(true);
app = {project: diagnostic, exitAfterLaunchAndEval: false,
  effects: [{matchName: 'S_A', displayName: 'Effect A'}, {matchName: 'S_B', displayName: 'Effect B'}],
  findMenuCommandId(name) {lookups++; return calls ? 2452 : name === 'Effect A' ? -101 : -102;},
  executeCommand(id) {
    assert.ok(id < 0, 'Do not treat negative IDs as invalid or call Repeat'); calls++;
    active.effects.push(makeEffect(scenario === 'wrong-effect' ? 'S_Wrong' : id === -101 ? 'S_A' : 'S_B'));
    if (scenario === 'takeover') app.project = user;
  }
};
const context = {app, File, Folder, ImportOptions: function () {},
  CloseOptions: {DO_NOT_SAVE_CHANGES: 0}, PropertyType: {PROPERTY: 1},
  PropertyValueType: {CUSTOM_VALUE: 3, NO_VALUE: 4}, Error, String};
let thrown;
try { vm.runInNewContext(fs.readFileSync(process.argv[2], 'utf8'), context, {timeout: 2000}); }
catch (e) { thrown = e; }
const comments = diagnostic.entries.map(x => x.comment || '').join('\n');
assert.equal(userSaves, 0); assert.equal(userCloses, 0);
if (scenario === 'success') {
  assert.ifError(thrown); assert.equal(calls, 5); assert.equal(lookups, 2);
  assert.ok(comments.includes('ALL_ADDED 5'));
  assert.equal((comments.match(/REPAIR_BEGIN/g) || []).length, 5);
  assert.equal(diagnostic.closed, true);
} else if (scenario === 'takeover') {
  assert.ifError(thrown); assert.equal(calls, 1); assert.equal(app.project, user);
  assert.equal(app.exitAfterLaunchAndEval, false); assert.ok(!comments.includes('ALL_ADDED'));
} else if (scenario === 'wrong-effect') {
  assert.ifError(thrown); assert.ok(comments.includes('PROBE_ERROR')); assert.ok(!comments.includes('ALL_ADDED'));
  assert.equal(diagnostic.closed, true);
} else if (scenario === 'existing') {
  assert.ok(thrown); assert.equal(calls, 0); assert.equal(diagnostic.closed, undefined);
} else throw new Error('Unknown scenario');
console.log(JSON.stringify({scenario, passed: true, calls, lookups}));
