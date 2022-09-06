'use strict'

const mqemitter = require('.')

const mq = mqemitter()

function subscribe (topic, obj) {
  mq.on(topic, callback)
  obj.close = close

  function callback (value, cb) {
    obj.push(value)
    cb()
  }

  function close () {
    mq.removeListener(topic, callback)
  }
}

class MyQueue {
  push (value) {
    console.log(value)
  }
}

const a = new MyQueue()
const b = new MyQueue()
const c = new MyQueue()

subscribe('hello', a)
subscribe('hello', b)
subscribe('hello', c)

mq.emit({ topic: 'hello', payload: 'world' })

a.close()
b.close()
c.close()

mq.emit({ topic: 'hello', payload: 'world' })

// const listeners = new Map()
//
//
// const queues = new Map()
//
// function subscribe (topic, queue) {
//   if (listeners.has(topic)) {
//
//   }
//
//   function callback (err) {
//
//     for (var value of queues) {
//     }
//   }
//
//   listeners.set(topic, callback)
//   queues.set(topic, [queue])
// }
