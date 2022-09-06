'use strict'

const test = require('tape').test
const memory = require('./')
const abs = require('./abstract')

abs({
  test,
  persistence: memory
})
