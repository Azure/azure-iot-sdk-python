'use strict'

var reusify = require('reusify')
var empty = []

function fastfall (context, template) {
  if (Array.isArray(context)) {
    template = context
    context = null
  }

  var queue = reusify(Holder)

  return template ? compiled : fall

  function fall () {
    var current = queue.get()
    current.release = release

    if (arguments.length === 3) {
      current.context = arguments[0]
      current.list = arguments[1]
      current.callback = arguments[2] || noop
    } else {
      current.context = context
      current.list = arguments[0]
      current.callback = arguments[1] || noop
    }

    current.work()
  }

  function release (holder) {
    queue.release(holder)
  }

  function compiled () {
    var current = queue.get()
    current.release = release

    current.list = template

    var args
    var i
    var len = arguments.length - 1

    current.context = this || context
    current.callback = arguments[len] || noop

    switch (len) {
      case 0:
        current.work()
        break
      case 1:
        current.work(null, arguments[0])
        break
      case 2:
        current.work(null, arguments[0], arguments[1])
        break
      case 3:
        current.work(null, arguments[0], arguments[1], arguments[2])
        break
      case 4:
        current.work(null, arguments[0], arguments[1], arguments[2], arguments[3])
        break
      default:
        args = new Array(len + 1)
        args[0] = null
        for (i = 0; i < len; i++) {
          args[i + 1] = arguments[i]
        }
        current.work.apply(null, args)
    }
  }
}

function noop () {}

function Holder () {
  this.list = empty
  this.callback = noop
  this.count = 0
  this.context = undefined
  this.release = noop

  var that = this

  this.work = function work () {
    if (arguments.length > 0 && arguments[0]) {
      return that.callback.call(that.context, arguments[0])
    }

    var len = arguments.length
    var i
    var args
    var func

    if (that.count < that.list.length) {
      func = that.list[that.count++]
      switch (len) {
        case 0:
        case 1:
          return func.call(that.context, work)
        case 2:
          return func.call(that.context, arguments[1], work)
        case 3:
          return func.call(that.context, arguments[1], arguments[2], work)
        case 4:
          return func.call(that.context, arguments[1], arguments[2], arguments[3], work)
        default:
          args = new Array(len)
          for (i = 1; i < len; i++) {
            args[i - 1] = arguments[i]
          }
          args[len - 1] = work
          func.apply(that.context, args)
      }
    } else {
      switch (len) {
        case 0:
          that.callback.call(that.context)
          break
        case 1:
          that.callback.call(that.context, arguments[0])
          break
        case 2:
          that.callback.call(that.context, arguments[0], arguments[1])
          break
        case 3:
          that.callback.call(that.context, arguments[0], arguments[1], arguments[2])
          break
        case 4:
          that.callback.call(that.context, arguments[0], arguments[1], arguments[2], arguments[3])
          break
        default:
          args = new Array(len)
          for (i = 0; i < len; i++) {
            args[i] = arguments[i]
          }
          that.callback.apply(that.context, args)
      }
      that.context = undefined
      that.list = empty
      that.count = 0
      that.release(that)
    }
  }
}

module.exports = fastfall
