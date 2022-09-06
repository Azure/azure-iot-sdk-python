var tape = require('tape')
var bulk = require('./')

tape('input matches', function (t) {
  var expected = ['a', 'b', 'c', 'd']
  var clone = expected.slice(0)

  var ws = bulk.obj(function (list, cb) {
    while (list.length) t.same(list.shift(), expected.shift())
    process.nextTick(cb)
  })

  for (var i = 0; i < clone.length; i++) ws.write(clone[i])

  ws.end(function () {
    t.end()
  })
})

tape('bulk list', function (t) {
  var expected = [['a'], ['b', 'c', 'd']]

  var ws = bulk.obj(function (list, cb) {
    t.same(list, expected.shift())
    process.nextTick(cb)
  })

  ws.write('a')
  ws.write('b')
  ws.write('c')
  ws.write('d')

  ws.end(function () {
    t.end()
  })
})

tape('flush one', function (t) {
  var expected = [[Buffer.from('a')]]
  var flushed = false

  var ws = bulk(function (list, cb) {
    t.same(list, expected.shift())
    process.nextTick(cb)
  }, function (cb) {
    flushed = true
    cb()
  })

  ws.write('a')

  ws.end(function () {
    t.ok(flushed)
    t.end()
  })
})

tape('flush', function (t) {
  var expected = [['a'], ['b', 'c', 'd']]
  var flushed = false

  var ws = bulk.obj(function (list, cb) {
    t.same(list, expected.shift())
    process.nextTick(cb)
  }, function (cb) {
    flushed = true
    cb()
  })

  ws.write('a')
  ws.write('b')
  ws.write('c')
  ws.write('d')

  ws.end(function () {
    t.ok(flushed)
    t.end()
  })
})

tape('flush binary', function (t) {
  var expected = [[Buffer.from('a')], [Buffer.from('b'), Buffer.from('c'), Buffer.from('d')]]
  var flushed = false

  var ws = bulk.obj(function (list, cb) {
    t.same(list, expected.shift())
    process.nextTick(cb)
  }, function (cb) {
    flushed = true
    cb()
  })

  ws.write(Buffer.from('a'))
  ws.write(Buffer.from('b'))
  ws.write(Buffer.from('c'))
  ws.write(Buffer.from('d'))

  ws.end(function () {
    t.ok(flushed)
    t.end()
  })
})
