#!/usr/bin/env node
'use strict';
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),{spawnSync}=require('node:child_process');
const tools=path.resolve(process.env.CODA_FIREBASE_TEST_TOOLS||'/tmp/coda-classroom-emulator');
const cli=path.join(tools,'node_modules/firebase-tools/lib/bin/firebase.js'),root=path.resolve(__dirname,'..');
const preload=path.resolve(root,'../coda-arcade/tools/firebase-emulator-loopback.cjs');
if(!fs.existsSync(cli)||!fs.existsSync(preload))throw Error('Use the isolated Firebase toolchain and sibling Coda emulator loopback preloader.');
const work=fs.mkdtempSync(path.join(os.tmpdir(),'coda-pitch-rules-')),config=path.join(work,'firebase.json');
fs.writeFileSync(config,JSON.stringify({database:{rules:path.join(root,'tests/fixtures/multiplayer-rules-before.json')},emulators:{database:{host:'127.0.0.1',port:9134},hub:{host:'127.0.0.1',port:4444},logging:{host:'127.0.0.1',port:4544},ui:{enabled:false},singleProjectMode:false}},null,2));
const quote=s=>"'"+s.replace(/'/g,"'\"'\"'")+"'";
const command=quote(process.execPath)+' --require '+quote(preload)+' --test '+quote(path.join(root,'tests/multiplayer-rules.emulator.cjs'));
const result=spawnSync(process.execPath,['--require',preload,cli,'emulators:exec','--only','database','--project','demo-coda-pitch-rules','--config',config,'--non-interactive',command],{cwd:work,stdio:'inherit',env:{...process.env,CODA_FIREBASE_TEST_TOOLS:tools,CODA_FIREBASE_LOOPBACK_PROXY:'1',FIREBASE_EMULATORS_PATH:path.join(tools,'emulator-cache'),XDG_CONFIG_HOME:path.join(tools,'cli-config')}});
process.stderr.write('Loopback emulator logs: '+work+'\n');
process.exitCode=typeof result.status==='number'?result.status:1;
