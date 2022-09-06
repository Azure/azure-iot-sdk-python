'use strict'

var xtend = require('xtend')
var reusify = require('reusify')
var defaults = {
  released: nop,
  results: true
}

function fastparallel (options) {
  options = xtend(defaults, options)

  var released = options.released
  var queue = reusify(options.results ? ResultsHolder : NoResultsHolder)
  var queueSingleCaller = reusify(SingleCaller)
  var goArray = options.results ? goResultsArray : goNoResultsArray
  var goFunc = options.results ? goResultsFunc : goNoResultsFunc

  return parallel

  function parallel (that, toCall, arg, done) {
    var holder = queue.get()
    done = done || nop
    if (toCall.length === 0) {
      done.call(that)
      released(holder)
    } else {
      holder._callback = done
      holder._callThat = that
      holder._release = release

      if (typeof toCall === 'function') {
        goFunc(that, toCall, arg, holder)
      } else {
        goArray(that, toCall, arg, holder)
      }

      if (holder._count === 0) {
        holder.release()
      }
    }
  }

  function release (holder) {
    queue.release(holder)
    released(holder)
  }

  function singleCallerRelease (holder) {
    queueSingleCaller.release(holder)
  }

  function goResultsFunc (that, toCall, arg, holder) {
    var singleCaller = null
    holder._count = arg.length
    holder._results = new Array(holder._count)
    for (var i = 0; i < arg.length; i++) {
      singleCaller = queueSingleCaller.get()
      singleCaller._release = singleCallerRelease
      singleCaller.parent = holder
      singleCaller.pos = i
      if (that) {
        toCall.call(that, arg[i], singleCaller.release)
      } else {
        toCall(arg[i], singleCaller.release)
      }
    }
  }

  function goResultsArray (that, funcs, arg, holder) {
    var sc = null
    var tc = nop
    holder._count = funcs.length
    holder._results = new Array(holder._count)
    for (var i = 0; i < funcs.length; i++) {
      sc = queueSingleCaller.get()
      sc._release = singleCallerRelease
      sc.parent = holder
      sc.pos = i
      tc = funcs[i]
      if (that) {
        if (tc.length === 1) tc.call(that, sc.release)
        else tc.call(that, arg, sc.release)
      } else {
        if (tc.length === 1) tc(sc.release)
        else tc(arg, sc.release)
      }
    }
  }

  function goNoResultsFunc (that, toCall, arg, holder) {
    holder._count = arg.length
    for (var i = 0; i < arg.length; i++) {
      if (that) {
        toCall.call(that, arg[i], holder.release)
      } else {
        toCall(arg[i], holder.release)
      }
    }
  }

  function goNoResultsArray (that, funcs, arg, holder) {
    var toCall = null
    holder._count = funcs.length
    for (var i = 0; i < funcs.length; i++) {
      toCall = funcs[i]
      if (that) {
        if (toCall.length === 1) {
          toCall.call(that, holder.release)
        } else {
          toCall.call(that, arg, holder.release)
        }
      } else {
        if (toCall.length === 1) {
          toCall(holder.release)
        } else {
          toCall(arg, holder.release)
        }
      }
    }
  }
}

function NoResultsHolder () {
  this._count = -1
  this._callback = nop
  this._callThat = null
  this._release = null
  this.next = null

  var that = this
  var i = 0
  this.release = function () {
    var cb = that._callback
    if (++i === that._count || that._count === 0) {
      if (that._callThat) {
        cb.call(that._callThat)
      } else {
        cb()
      }
      that._callback = nop
      that._callThat = null
      i = 0
      that._release(that)
    }
  }
}

function SingleCaller () {
  this.pos = -1
  this._release = nop
  this.parent = null
  this.next = null

  var that = this
  this.release = function (err, result) {
    that.parent.release(err, that.pos, result)
    that.pos = -1
    that.parent = null
    that._release(that)
  }
}

function ResultsHolder () {
  this._count = -1
  this._callback = nop
  this._results = null
  this._err = null
  this._callThat = null
  this._release = nop
  this.next = null

  var that = this
  var i = 0
  this.release = function (err, pos, result) {
    that._err = that._err || err
    if (pos >= 0) {
      that._results[pos] = result
    }
    var cb = that._callback
    if (++i === that._count || that._count === 0) {
      if (that._callThat) {
        cb.call(that._callThat, that._err, that._results)
      } else {
        cb(that._err, that._results)
      }
      that._callback = nop
      that._results = null
      that._err = null
      that._callThat = null
      i = 0
      that._release(that)
    }
  }
}

function nop () { }

module.exports = fastparallel
