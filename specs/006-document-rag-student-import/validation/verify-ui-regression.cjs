// Reuse the graphics/IDE acceptance suite; keep feature 004 evidence unchanged.
const fs = require('fs');
const path = require('path');
const Module = require('module');
const filename = path.resolve(__dirname, '../../004-ocean-station-ui/validation/verify-ui.cjs');
const script = fs.readFileSync(filename, 'utf8')
  .replace('const output = __dirname;', `const output = ${JSON.stringify(__dirname)};`)
  .replace("'ui-results.json'", "'legacy-ui-results.json'");
const acceptance = new Module(filename, module);
acceptance.filename = filename;
acceptance.paths = module.paths;
acceptance._compile(script, filename);
