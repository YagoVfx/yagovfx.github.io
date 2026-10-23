// Pass explicit filenames: quoted globs behave differently across Node versions.
const { readdirSync } = require('node:fs');
const { join, resolve } = require('node:path');
const { spawnSync } = require('node:child_process');
const folder = resolve(__dirname, '../tests/js');
const files = readdirSync(folder).filter(name => name.endsWith('.test.js')).sort().map(name => join(folder, name));
if (!files.length) throw new Error('No JavaScript test files found');
const result = spawnSync(process.execPath, ['--test', ...files], { stdio: 'inherit' });
if (result.error) throw result.error;
process.exit(result.status ?? 1);
