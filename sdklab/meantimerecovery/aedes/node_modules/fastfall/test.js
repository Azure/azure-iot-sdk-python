'use strict'

var test = require('tape')
var fastfall = require('./')

test('basically works', function (t) {
  t.plan(22)

  var fall = fastfall()

  fall([
    function a (cb) {
      cb(null, 'a')
    },
    function b (a, cb) {
      t.equal(a, 'a', 'second function arg matches')
      cb(null, 'a', 'b')
    },
    function c (a, b, cb) {
      t.equal(a, 'a', 'third function 1st arg matches')
      t.equal(b, 'b', 'third function 2nd arg matches')
      cb(null, 'a', 'b', 'c')
    },
    function d (a, b, c, cb) {
      t.equal(a, 'a', 'fourth function 1st arg matches')
      t.equal(b, 'b', 'fourth function 2nd arg matches')
      t.equal(c, 'c', 'fourth function 3rd arg matches')
      cb(null, 'a', 'b', 'c', 'd')
    },
    function e (a, b, c, d, cb) {
      t.equal(a, 'a', 'fifth function 1st arg matches')
      t.equal(b, 'b', 'fifth function 2nd arg matches')
      t.equal(c, 'c', 'fifth function 3rd arg matches')
      t.equal(d, 'd', 'fifth function 4th arg matches')
      cb(null, 'a', 'b', 'c', 'd', 'e')
    },
    function f (a, b, c, d, e, cb) {
      t.equal(a, 'a', 'sixth function 1st arg matches')
      t.equal(b, 'b', 'sixth function 2nd arg matches')
      t.equal(c, 'c', 'sixth function 3rd arg matches')
      t.equal(d, 'd', 'sixth function 4th arg matches')
      t.equal(e, 'e', 'sixth function 5th arg matches')
      cb(null, 'a', 'b', 'c', 'd', 'e', 'f')
    }
  ], function result (err, a, b, c, d, e, f) {
    t.error(err, 'no error')
    t.equal(a, 'a', 'result function 2nd arg matches')
    t.equal(b, 'b', 'result function 3rd arg matches')
    t.equal(c, 'c', 'result function 4th arg matches')
    t.equal(d, 'd', 'result function 5th arg matches')
    t.equal(e, 'e', 'result function 6th arg matches')
    t.equal(f, 'f', 'result function 7th arg matches')
  })
})

test('call with error', function (t) {
  t.plan(4)

  var fall = fastfall()

  fall([
    function a (cb) {
      cb(null, 'a')
    },
    function b (a, cb) {
      t.equal(a, 'a', 'second function arg matches')
      cb(new Error('this is expected!'), 'a', 'b')
    },
    function c (a, b, cb) {
      t.fail('this should never happen')
    }
  ], function result (err, a, b, c) {
    t.ok(err, 'error')
    t.notOk(a, 'no 2nd arg')
    t.notOk(b, 'no 3rd arg')
  })
})

test('compiles a reusable fall', function (t) {
  t.plan(10)

  var fall = fastfall([
    function a (arg, cb) {
      cb(null, arg)
    },
    function b (a, cb) {
      cb(null, a, 'b')
    },
    function c (a, b, cb) {
      t.equal(b, 'b', 'third function 2nd arg matches')
      cb(null, a, 'b', 'c')
    }
  ])

  fall(42, function result (err, a, b, c) {
    t.error(err, 'no error')
    t.equal(a, 42, 'result function 2nd arg matches')
    t.equal(b, 'b', 'result function 3rd arg matches')
    t.equal(c, 'c', 'result function 4th arg matches')
  })

  fall(24, function result (err, a, b, c) {
    t.error(err, 'no error')
    t.equal(a, 24, 'result function 2nd arg matches')
    t.equal(b, 'b', 'result function 3rd arg matches')
    t.equal(c, 'c', 'result function 4th arg matches')
  })
})

test('set this', function (t) {
  t.plan(2)

  var that = {}
  var fall = fastfall(that)

  fall([
    function a (cb) {
      t.equal(this, that, 'this is set')
      cb(null, 'a')
    }
  ], function result (err, a, b, c) {
    t.error(err, 'no error')
  })
})

test('set this in compiled mode', function (t) {
  t.plan(4)

  var that = {}
  var fall = fastfall(that, [
    function a (arg, cb) {
      t.equal(this, that, 'this is set')
      cb(null, arg)
    }
  ])

  fall(42, function result (err, a, b, c) {
    t.error(err, 'no error')
    t.equal(a, 42, 'result function 2nd arg matches')
    t.equal(this, that, 'this is set')
  })
})

test('set this for a normal fall', function (t) {
  t.plan(4)

  var that = {}
  var fall = fastfall()

  fall(that, [
    function a (cb) {
      t.equal(this, that, 'this is set')
      cb(null, 'a')
    }
  ], function result (err, a) {
    t.error(err, 'no error')
    t.equal(this, that, 'this is set')
    t.equal(a, 'a', 'result function 2nd arg matches')
  })
})

test('use the this of the called object in compiled mode', function (t) {
  t.plan(4)

  var that = {}
  var fall = fastfall([
    function a (arg, cb) {
      t.equal(this, that, 'this is set')
      cb(null, arg)
    }
  ])

  fall.call(that, 42, function result (err, a, b, c) {
    t.error(err, 'no error')
    t.equal(a, 42, 'result function 2nd arg matches')
    t.equal(this, that, 'this is set')
  })
})

test('support errors in compiled mode', function (t) {
  t.plan(2)

  var fall = fastfall([
    function a (arg, cb) {
      t.pass('function is called')
      cb(new Error('muahaha'), arg)
    }
  ])

  fall(42, function result (err) {
    t.ok(err, 'error is forwarded')
  })
})
