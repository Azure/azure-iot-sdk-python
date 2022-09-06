var max = 1000000
var parallel = require('./')()
var parallelNoResults = require('./')({ results: false })
var bench = require('fastbench')
var async = require('async')
var neo = require('neo-async')

var funcs = []

for (var i = 0; i < 25; i++) {
  funcs.push(something)
}

function benchFastParallel (done) {
  parallel(null, funcs, 42, done)
}

function benchFastParallelNoResults (done) {
  parallelNoResults(null, funcs, 42, done)
}

function benchAsyncParallel (done) {
  async.parallel(funcs, done)
}

function benchNeoParallel (done) {
  neo.parallel(funcs, done)
}

function something (cb) {
  setImmediate(cb)
}

var run = bench([
  benchAsyncParallel,
  benchNeoParallel,
  benchFastParallel,
  benchFastParallelNoResults
], max)

run(run)
