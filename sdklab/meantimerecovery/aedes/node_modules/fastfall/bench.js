'use strict'

var max = 100000
var async = require('async')
var insync = require('insync')
var neoAsync = require('neo-async')
var fall = require('./')()
var runWaterfall = require('run-waterfall')
var waterfallize = require('waterfallize')
var bench = require('fastbench')

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

function somethingB (cb) {
  setImmediate(cb)
}

function somethingA (cb) {
  setImmediate(cb)
}

var toCall = [somethingA, somethingB, somethingB]
function benchAsyncWaterfall (done) {
  async.waterfall(toCall, done)
}

function benchFastFall (done) {
  fall(toCall, done)
}

function benchWaterfallize (done) {
  var next = waterfallize()

  next(toCall[0])
  next(toCall[1])
  next(toCall[2])
  next(done)
}

function benchRunWaterFall (done) {
  runWaterfall(toCall, done)
}

function benchInsync (done) {
  insync.waterfall(toCall, done)
}

function benchNeoAsync (done) {
  neoAsync.waterfall(toCall, done)
}

var compiled = require('./')(toCall)

var run = bench([
  benchAsyncWaterfall,
  benchInsync,
  benchNeoAsync,
  benchRunWaterFall,
  benchSetImmediate,
  benchWaterfallize,
  benchFastFall,
  compiled
], max)

run(run)
