var max = 1000000
var series = require('./')()
var seriesNoResults = require('./')({ results: false })
var async = require('async')
var neo = require('neo-async')
var bench = require('fastbench')
var tinyEachAsync = require('tiny-each-async')

function benchFastSeries (done) {
  series(null, [somethingP, somethingP, somethingP], 42, done)
}

function benchFastSeriesNoResults (done) {
  seriesNoResults(null, [somethingP, somethingP, somethingP], 42, done)
}

function benchFastSeriesEach (done) {
  seriesNoResults(null, somethingP, [1, 2, 3], done)
}

function benchFastSeriesEachResults (done) {
  series(null, somethingP, [1, 2, 3], done)
}

function benchAsyncSeries (done) {
  async.series([somethingA, somethingA, somethingA], done)
}

function benchAsyncEachSeries (done) {
  async.eachSeries([1, 2, 3], somethingP, done)
}

function benchAsyncMapSeries (done) {
  async.mapSeries([1, 2, 3], somethingP, done)
}

function benchNeoSeries (done) {
  neo.series([somethingA, somethingA, somethingA], done)
}

function benchNeoEachSeries (done) {
  neo.eachSeries([1, 2, 3], somethingP, done)
}

function benchNeoMapSeries (done) {
  neo.mapSeries([1, 2, 3], somethingP, done)
}

function benchTinyEachAsync (done) {
  tinyEachAsync([1, 2, 3], 1, somethingP, done)
}

var nextDone
var nextCount

function benchSetImmediate (done) {
  nextCount = 3
  nextDone = done
  setImmediate(somethingImmediate)
}

function somethingImmediate () {
  nextCount--
  if (nextCount === 0) {
    nextDone()
  } else {
    setImmediate(somethingImmediate)
  }
}

function somethingP (arg, cb) {
  setImmediate(cb)
}

function somethingA (cb) {
  setImmediate(cb)
}

var run = bench([
  benchSetImmediate,
  benchAsyncSeries,
  benchAsyncEachSeries,
  benchAsyncMapSeries,
  benchNeoSeries,
  benchNeoEachSeries,
  benchNeoMapSeries,
  benchTinyEachAsync,
  benchFastSeries,
  benchFastSeriesNoResults,
  benchFastSeriesEach,
  benchFastSeriesEachResults
], max)

run(run)
