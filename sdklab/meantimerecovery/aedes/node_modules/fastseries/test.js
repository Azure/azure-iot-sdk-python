'use strict'

var test = require('tape')
var series = require('./')

test('basically works', function (t) {
  t.plan(7)

  var instance = series()
  var count = 0
  var obj = {}

  instance(obj, [build(0), build(1)], 42, function done () {
    t.equal(count, 2, 'all functions must have completed')
  })

  function build (expected) {
    return function something (arg, cb) {
      t.equal(obj, this)
      t.equal(arg, 42)
      t.equal(expected, count)
      setImmediate(function () {
        count++
        cb()
      })
    }
  }
})

test('without this', function (t) {
  t.plan(7)

  var instance = series()
  var count = 0

  instance(null, [build(0), build(1)], 42, function done () {
    t.equal(count, 2, 'all functions must have completed')
  })

  function build (expected) {
    return function something (arg, cb) {
      t.equal(undefined, this)
      t.equal(arg, 42)
      t.equal(expected, count)
      setImmediate(function () {
        count++
        cb()
      })
    }
  }
})

test('accumulates results', function (t) {
  t.plan(7)

  var instance = series()
  var count = 0
  var obj = {}

  instance(obj, [something, something], 42, function done (err, results) {
    t.notOk(err, 'no error')
    t.equal(count, 2, 'all functions must have completed')
    t.deepEqual(results, [1, 2])
  })

  function something (arg, cb) {
    t.equal(obj, this)
    t.equal(arg, 42)
    setImmediate(function () {
      count++
      cb(null, count)
    })
  }
})

test('fowards errs', function (t) {
  t.plan(3)

  var instance = series()
  var count = 0
  var obj = {}

  instance(obj, [somethingErr, something], 42, function done (err, results) {
    t.ok(err, 'error exists')
    t.equal(err.message, 'this is an err!')
    t.equal(count, 1, 'only the first function must have completed')
  })

  function something (arg, cb) {
    setImmediate(function () {
      count++
      cb(null, count)
    })
  }

  function somethingErr (arg, cb) {
    setImmediate(function () {
      count++
      cb(new Error('this is an err!'))
    })
  }
})

test('does not forward errors or result with results:false flag', function (t) {
  t.plan(7)

  var instance = series({
    results: false
  })
  var count = 0
  var obj = {}

  instance(obj, [something, something], 42, function done (err, results) {
    t.equal(err, undefined, 'no err')
    t.equal(results, undefined, 'no err')
    t.equal(count, 2, 'all functions must have completed')
  })

  function something (arg, cb) {
    t.equal(obj, this)
    t.equal(arg, 42)
    setImmediate(function () {
      count++
      cb()
    })
  }
})

test('should call done iff an empty is passed', function (t) {
  t.plan(1)

  var instance = series()
  var obj = {}

  instance(obj, [], 42, function done () {
    t.pass()
  })
})

test('each support', function (t) {
  t.plan(7)

  var instance = series()
  var count = 0
  var obj = {}
  var args = [1, 2, 3]
  var i = 0

  instance(obj, something, [].concat(args), function done () {
    t.equal(count, 3, 'all functions must have completed')
  })

  function something (arg, cb) {
    t.equal(obj, this, 'this matches')
    t.equal(args[i++], arg, 'the arg is correct')
    setImmediate(function () {
      count++
      cb()
    })
  }
})

test('each errors', function (t) {
  t.plan(2)

  var instance = series()
  var obj = {}
  var args = [1, 2, 3]
  var err = new Error('kaboom')

  instance(obj, something, [].concat(args), function done (_err) {
    t.equal(err, _err)
  })

  function something (arg, cb) {
    t.pass('something called')
    cb(err)
  }
})

test('each without this', function (t) {
  t.plan(7)

  var instance = series()
  var count = 0
  var args = [1, 2, 3]
  var i = 0

  instance(null, something, [].concat(args), function done () {
    t.equal(count, 3, 'all functions must have completed')
  })

  function something (arg, cb) {
    t.equal(undefined, this, 'this matches')
    t.equal(args[i++], arg, 'the arg is correct')
    setImmediate(function () {
      count++
      cb()
    })
  }
})

test('call the callback with the given this', function (t) {
  t.plan(1)

  var instance = series()
  var obj = {}

  instance(obj, [build(), build()], 42, function done () {
    t.equal(obj, this, 'this matches')
  })

  function build () {
    return function something (arg, cb) {
      setImmediate(cb)
    }
  }
})

test('call the callback with the given this with no results', function (t) {
  t.plan(1)

  var instance = series({ results: false })
  var obj = {}

  instance(obj, [build(), build()], 42, function done () {
    t.equal(obj, this, 'this matches')
  })

  function build () {
    return function something (arg, cb) {
      setImmediate(cb)
    }
  }
})

test('call the callback with the given this with no data', function (t) {
  t.plan(1)

  var instance = series()
  var obj = {}

  instance(obj, [], 42, function done () {
    t.equal(obj, this, 'this matches')
  })
})

test('support no final callback', function (t) {
  t.plan(6)

  var instance = series()
  var count = 0
  var obj = {}

  instance(obj, [build(0), build(1)], 42)

  function build (expected) {
    return function something (arg, cb) {
      t.equal(obj, this)
      t.equal(arg, 42)
      t.equal(expected, count)
      setImmediate(function () {
        count++
        cb()
      })
    }
  }
})

test('call without arg if there is no arg with no results', function (t) {
  t.plan(3)

  var instance = series({
    results: false
  })
  var count = 0
  var obj = {}

  instance(obj, [something, something], 42, function done () {
    t.equal(count, 2, 'all functions must have completed')
  })

  function something (cb) {
    t.equal(obj, this)
    setImmediate(function () {
      count++
      cb()
    })
  }
})

test('call without arg if there is no arg with results', function (t) {
  t.plan(3)

  var instance = series()
  var count = 0
  var obj = {}

  instance(obj, [something, something], 42, function done () {
    t.equal(count, 2, 'all functions must have completed')
  })

  function something (cb) {
    t.equal(obj, this)
    setImmediate(function () {
      count++
      cb()
    })
  }
})

test('each support with nothing to process', function (t) {
  t.plan(2)

  var instance = series()
  var obj = {}
  var args = []

  instance(obj, something, args, function done (err, results) {
    t.error(err)
    t.deepEqual(results, [], 'empty results')
  })

  function something (arg, cb) {
    t.fail('this should never happen')
  }
})

test('each without results support with nothing to process', function (t) {
  t.plan(1)

  var instance = series({ results: false })
  var obj = {}
  var args = []

  instance(obj, something, args, function done () {
    t.pass('done called')
  })

  function something (arg, cb) {
    t.fail('this should never happen')
  }
})

test('each without results', function (t) {
  t.plan(7)

  var instance = series({
    results: false
  })
  var count = 0
  var obj = {}
  var args = [1, 2, 3]
  var i = 0

  instance(obj, something, [].concat(args), function done () {
    t.equal(count, 3, 'all functions must have completed')
  })

  function something (arg, cb) {
    t.equal(obj, this, 'this matches')
    t.equal(args[i++], arg, 'the arg is correct')
    setImmediate(function () {
      count++
      cb()
    })
  }
})
