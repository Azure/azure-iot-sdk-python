'use strict'

const mqemitter = require('./')
const emitter = mqemitter({ concurrency: 10 })
const total = 1000000
let written = 0
let received = 0
const timerKey = 'time for sending ' + total + ' messages'

function write () {
  if (written === total) {
    return
  }

  written++

  emitter.emit({ topic: 'hello', payload: 'world' }, write)
}

emitter.on('hello', function (msg, cb) {
  received++
  if (received === total) {
    console.timeEnd(timerKey)
  }
  setImmediate(cb)
})

console.time(timerKey)
write()
write()
write()
write()
write()
write()
write()
write()
write()
write()
write()
write()
