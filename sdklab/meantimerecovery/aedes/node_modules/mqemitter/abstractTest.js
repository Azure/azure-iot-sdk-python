
'use strict'

module.exports = function abstractTests (opts) {
  const builder = opts.builder
  const test = opts.test

  test('support on and emit', function (t) {
    t.plan(4)

    const e = builder()
    const expected = {
      topic: 'hello world',
      payload: { my: 'message' }
    }

    e.on('hello world', function (message, cb) {
      t.equal(e.current, 1, 'number of current messages')
      t.deepEqual(message, expected)
      t.equal(this, e)
      cb()
    }, function () {
      e.emit(expected, function () {
        e.close(function () {
          t.pass('closed')
        })
      })
    })
  })

  test('support multiple subscribers', function (t) {
    t.plan(3)

    const e = builder()
    const expected = {
      topic: 'hello world',
      payload: { my: 'message' }
    }

    e.on('hello world', function (message, cb) {
      t.ok(message, 'message received')
      cb()
    }, function () {
      e.on('hello world', function (message, cb) {
        t.ok(message, 'message received')
        cb()
      }, function () {
        e.emit(expected, function () {
          e.close(function () {
            t.pass('closed')
          })
        })
      })
    })
  })

  test('support multiple subscribers and unsubscribers', function (t) {
    t.plan(2)

    const e = builder()
    const expected = {
      topic: 'hello world',
      payload: { my: 'message' }
    }

    function first (message, cb) {
      t.fail('first listener should not receive any events')
      cb()
    }

    function second (message, cb) {
      t.ok(message, 'second listener must receive the message')
      cb()
      e.close(function () {
        t.pass('closed')
      })
    }

    e.on('hello world', first, function () {
      e.on('hello world', second, function () {
        e.removeListener('hello world', first, function () {
          e.emit(expected)
        })
      })
    })
  })

  test('removeListener', function (t) {
    t.plan(1)

    const e = builder()
    const expected = {
      topic: 'hello world',
      payload: { my: 'message' }
    }
    let toRemoveCalled = false

    function toRemove (message, cb) {
      toRemoveCalled = true
      cb()
    }

    e.on('hello world', function (message, cb) {
      cb()
    }, function () {
      e.on('hello world', toRemove, function () {
        e.removeListener('hello world', toRemove, function () {
          e.emit(expected, function () {
            e.close(function () {
              t.notOk(toRemoveCalled, 'the toRemove function must not be called')
            })
          })
        })
      })
    })
  })

  test('without a callback on emit and on', function (t) {
    t.plan(1)

    const e = builder()
    const expected = {
      topic: 'hello world',
      payload: { my: 'message' }
    }

    e.on('hello world', function (message, cb) {
      cb()
      e.close(function () {
        t.pass('closed')
      })
    })

    setTimeout(function () {
      e.emit(expected)
    }, 100)
  })

  test('without any listeners', function (t) {
    t.plan(2)

    const e = builder()
    const expected = {
      topic: 'hello world',
      payload: { my: 'message' }
    }

    e.emit(expected)
    t.equal(e.current, 0, 'reset the current messages trackers')
    e.close(function () {
      t.pass('closed')
    })
  })

  test('support one level wildcard', function (t) {
    t.plan(2)

    const e = builder()
    const expected = {
      topic: 'hello/world',
      payload: { my: 'message' }
    }

    e.on('hello/+', function (message, cb) {
      t.equal(message.topic, 'hello/world')
      cb()
    }, function () {
      // this will not be catched
      e.emit({ topic: 'hello/my/world' })

      // this will be catched
      e.emit(expected, function () {
        e.close(function () {
          t.pass('closed')
        })
      })
    })
  })

  test('support one level wildcard - not match empty words', function (t) {
    t.plan(2)

    const e = builder({ matchEmptyLevels: false })
    const expected = {
      topic: 'hello/dummy/world',
      payload: { my: 'message' }
    }

    e.on('hello/+/world', function (message, cb) {
      t.equal(message.topic, 'hello/dummy/world')
      cb()
    }, function () {
      // this will not be catched
      e.emit({ topic: 'hello//world' })

      // this will be catched
      e.emit(expected, function () {
        e.close(function () {
          t.pass('closed')
        })
      })
    })
  })

  test('support one level wildcard - match empty words', function (t) {
    t.plan(3)

    const e = builder({ matchEmptyLevels: true })

    e.on('hello/+/world', function (message, cb) {
      const topic = message.topic
      if (topic === 'hello//world' || topic === 'hello/dummy/world') {
        t.pass('received ' + topic)
      }
      cb()
    }, function () {
      // this will be catched
      e.emit({ topic: 'hello//world' })
      // this will be catched
      e.emit({ topic: 'hello/dummy/world' }, function () {
        e.close(function () {
          t.pass('closed')
        })
      })
    })
  })

  test('support one level wildcard - match empty words', function (t) {
    t.plan(2)

    const e = builder({ matchEmptyLevels: true })

    e.on('hello/+', function (message, cb) {
      t.equal(message.topic, 'hello/')
      cb()
    }, function () {
      // this will be catched
      e.emit({ topic: 'hello/' }, function () {
        e.close(function () {
          t.pass('closed')
        })
      })
    })
  })

  test('support one level wildcard - not match empty words', function (t) {
    t.plan(1)

    const e = builder({ matchEmptyLevels: false })

    e.on('hello/+', function (message, cb) {
      t.fail('should not catch')
      cb()
    }, function () {
      // this will not be catched
      e.emit({ topic: 'hello/' }, function () {
        e.close(function () {
          t.pass('closed')
        })
      })
    })
  })

  test('support changing one level wildcard', function (t) {
    t.plan(2)

    const e = builder({ wildcardOne: '~' })
    const expected = {
      topic: 'hello/world',
      payload: { my: 'message' }
    }

    e.on('hello/~', function (message, cb) {
      t.equal(message.topic, 'hello/world')
      cb()
    }, function () {
      e.emit(expected, function () {
        e.close(function () {
          t.pass('closed')
        })
      })
    })
  })

  test('support deep wildcard', function (t) {
    t.plan(2)

    const e = builder()
    const expected = {
      topic: 'hello/my/world',
      payload: { my: 'message' }
    }

    e.on('hello/#', function (message, cb) {
      t.equal(message.topic, 'hello/my/world')
      cb()
    }, function () {
      e.emit(expected, function () {
        e.close(function () {
          t.pass('closed')
        })
      })
    })
  })

  test('support deep wildcard without separator', function (t) {
    t.plan(2)

    const e = builder()
    const expected = {
      topic: 'hello',
      payload: { my: 'message' }
    }

    e.on('#', function (message, cb) {
      t.equal(message.topic, expected.topic)
      cb()
    }, function () {
      e.emit(expected, function () {
        e.close(function () {
          t.pass('closed')
        })
      })
    })
  })

  test('support deep wildcard - match empty words', function (t) {
    t.plan(2)

    const e = builder({ matchEmptyLevels: true })
    const expected = {
      topic: 'hello',
      payload: { my: 'message' }
    }

    const wrong = {
      topic: 'hellooo',
      payload: { my: 'message' }
    }

    e.on('hello/#', function (message, cb) {
      t.equal(message.topic, expected.topic)
      cb()
    }, function () {
      e.emit(wrong) // this should not be received
      e.emit(expected, function () {
        e.close(function () {
          t.pass('closed')
        })
      })
    })
  })

  test('support changing deep wildcard', function (t) {
    t.plan(2)

    const e = builder({ wildcardSome: '*' })
    const expected = {
      topic: 'hello/my/world',
      payload: { my: 'message' }
    }

    e.on('hello/*', function (message, cb) {
      t.equal(message.topic, 'hello/my/world')
      cb()
    }, function () {
      e.emit(expected, function () {
        e.close(function () {
          t.pass('closed')
        })
      })
    })
  })

  test('support changing the level separator', function (t) {
    t.plan(2)

    const e = builder({ separator: '~' })
    const expected = {
      topic: 'hello~world',
      payload: { my: 'message' }
    }

    e.on('hello~+', function (message, cb) {
      t.equal(message.topic, 'hello~world')
      cb()
    }, function () {
      e.emit(expected, function () {
        e.close(function () {
          t.pass('closed')
        })
      })
    })
  })

  test('close support', function (t) {
    const e = builder()
    let check = false

    t.notOk(e.closed, 'must have a false closed property')

    e.close(function () {
      t.ok(check, 'must delay the close callback')
      t.ok(e.closed, 'must have a true closed property')
      t.end()
    })

    check = true
  })

  test('emit after close errors', function (t) {
    const e = builder()

    e.close(function () {
      e.emit({ topic: 'hello' }, function (err) {
        t.ok(err, 'must return an error')
        t.end()
      })
    })
  })

  test('support multiple subscribers with wildcards', function (t) {
    const e = builder()
    const expected = {
      topic: 'hello/world',
      payload: { my: 'message' }
    }
    let firstCalled = false
    let secondCalled = false

    e.on('hello/#', function (message, cb) {
      t.notOk(firstCalled, 'first subscriber must only be called once')
      firstCalled = true
      cb()
    })

    e.on('hello/+', function (message, cb) {
      t.notOk(secondCalled, 'second subscriber must only be called once')
      secondCalled = true
      cb()
    }, function () {
      e.emit(expected, function () {
        e.close(function () {
          t.end()
        })
      })
    })
  })

  test('support multiple subscribers with wildcards (deep)', function (t) {
    const e = builder()
    const expected = {
      topic: 'hello/my/world',
      payload: { my: 'message' }
    }
    let firstCalled = false
    let secondCalled = false

    e.on('hello/#', function (message, cb) {
      t.notOk(firstCalled, 'first subscriber must only be called once')
      firstCalled = true
      cb()
    })

    e.on('hello/+/world', function (message, cb) {
      t.notOk(secondCalled, 'second subscriber must only be called once')
      secondCalled = true
      cb()
    }, function () {
      e.emit(expected, function () {
        e.close(function () {
          t.end()
        })
      })
    })
  })

  test('emit & receive buffers', function (t) {
    const e = builder()
    const msg = Buffer.from('hello')
    const expected = {
      topic: 'hello',
      payload: msg
    }

    e.on('hello', function (message, cb) {
      t.deepEqual(msg, message.payload)
      cb()
    }, function () {
      e.emit(expected, function () {
        e.close(function () {
          t.end()
        })
      })
    })
  })

  test('packets are emitted in order', function (t) {
    const e = builder()
    const total = 10000
    const topic = 'test'

    let received = 0

    e.on(topic, function (msg, cb) {
      let fail = false
      if (received !== msg.payload) {
        t.fail(`leak detected. Count: ${received} - Payload: ${msg.payload}`)
        fail = true
      }

      received++

      if (fail || received === total) {
        e.close(function () {
          t.end()
        })
      }
      cb()
    })

    for (let payload = 0; payload < total; payload++) {
      e.emit({ topic, payload })
    }
  })

  test('calling emit without cb when closed doesn\'t throw error', function (t) {
    const e = builder()
    const msg = Buffer.from('hello')
    const expected = {
      topic: 'hello',
      payload: msg
    }

    e.close(function () {
      try {
        e.emit(expected)
      } catch (error) {
        t.error('throws error')
      }
      t.end()
    })
  })
}
