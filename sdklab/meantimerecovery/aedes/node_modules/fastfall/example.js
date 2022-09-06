'use strict'

var fall = require('./')()

fall([
  function a (cb) {
    console.log('called a')
    cb(null, 'a')
  },
  function b (a, cb) {
    console.log('called b with:', a)
    cb(null, 'a', 'b')
  },
  function c (a, b, cb) {
    console.log('called c with:', a, b)
    cb(null, 'a', 'b', 'c')
  }
], function result (err, a, b, c) {
  console.log('result arguments', err, a, b, c)
})
