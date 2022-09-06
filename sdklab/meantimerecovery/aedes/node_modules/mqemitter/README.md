<!-- markdownlint-disable MD013 MD024 -->

# MQEmitter

![ci](https://github.com/mcollina/mqemitter/workflows/ci/badge.svg)
[![Known Vulnerabilities](https://snyk.io/test/github/mcollina/mqemitter/badge.svg)](https://snyk.io/test/github/mcollina/mqemitter)
[![js-standard-style](https://img.shields.io/badge/code%20style-standard-brightgreen.svg?style=flat)](http://standardjs.com/)\
[![Dependencies Status](https://david-dm.org/mcollina/mqemitter/status.svg)](https://david-dm.org/mcollina/mqemitter)
[![devDependencies Status](https://david-dm.org/mcollina/mqemitter/dev-status.svg)](https://david-dm.org/mcollina/mqemitter?type=dev)\
[![NPM version](https://img.shields.io/npm/v/mqemitter.svg?style=flat)](https://www.npmjs.com/mqemitter)
[![NPM downloads](https://img.shields.io/npm/dm/mqemitter.svg?style=flat)](https://www.npmjs.com/mqemitter)

An Opinionated Message Queue with an emitter-style API, but with callbacks.

If you need a multi process MQEmitter, check out the table below:

- [mqemitter-redis]: Redis-powered mqemitter
- [mqemitter-mongodb]: Mongodb based mqemitter
- [mqemitter-child-process]: Share the same mqemitter between a hierarchy of child processes
- [mqemitter-cs]: Expose a MQEmitter via a simple client/server protocol
- [mqemitter-p2p]: A P2P implementation of MQEmitter, based on HyperEmitter and a Merkle DAG
- [mqemitter-aerospike]: Aerospike mqemitter

## Installation

```sh
npm install mqemitter
```

## Examples

```js
const mq = require('mqemitter')
const emitter = mq({ concurrency: 5 })
const message

emitter.on('hello world', function (message, cb) {
  // call callback when you are done
  // do not pass any errors, the emitter cannot handle it.
  cb()
})

// topic is mandatory
message = { topic: 'hello world', payload: 'or any other fields' }
emitter.emit(message, function () {
  // emitter will never return an error
})
```

## API

- [new MQEmitter ([options])](#new-mqemitter-options)
- [emitter.emit (message, callback)](#emitteremit-message-callback)
- [emitter.on (topic, listener, [callback])](#emitteron-topic-listener-callback)
- [emitter.removeListener (topic, listener, [callback])](#emitterremovelistener-topic-listener-callback)
- [emitter.close (callback)](#emitterclose-callback)

## new MQEmitter ([options])

- options `<object>`
  - `concurrency` `<number>` maximum number of concurrent messages that can be on concurrent delivery. __Default__: `0`
  - `wildcardOne` `<string>` a char to use for matching exactly one _non-empty_ level word. __Default__: `+`
  - `wildcardSome` `<string>` a char to use for matching multiple level wildcards. __Default__: #`
  - `matchEmptyLevels` `<boolean>` If true then `wildcardOne` also matches an empty word. __Default__: `true`
  - `separator` `<string>`  a separator character to use for separating words. __Default__: `/`

Create a new MQEmitter class.

MQEmitter is the class and function exposed by this module.
It can be created by `MQEmitter()` or using `new MQEmitter()`.

For more information on wildcards, see [this explanation](#wildcards) or [Qlobber](https://www.npmjs.com/qlobber).

## emitter.emit (message, callback)

- `message` `<object>`
- `callback` `<Function>` `(error) => void`
  - error `<Error>` | `null`

Emit the given message, which must have a `topic` property, which can contain wildcards as defined on creation.

## emitter.on (topic, listener, [callback])

- `topic` `<string>`
- `listener` `<Function>` `(message, done) => void`
- `callback` `<Function>` `() => void`

Add the given listener to the passed topic. Topic can contain wildcards, as defined on creation.

The `listener` __must never error__ and `done` must not be called with an __`err`__ object.

`callback` will be called when the event subscribe is done correctly.

## emitter.removeListener (topic, listener, [callback])

The inverse of `on`.

## emitter.close (callback)

- `callback` `<Function>` `() => void`

Close the given emitter. After, all writes will return an error.

## Wildcards

__MQEmitter__ supports the use of wildcards: every topic is splitted according to `separator`.

The wildcard character `+` matches exactly _non-empty_ one word:

```js
const mq = require('mqemitter')
const emitter = mq()

emitter.on('hello/+/world', function(message, cb) {
  // will ONLY capture { topic: 'hello/my/world', 'something': 'more' }
  console.log(message)
  cb()
})
emitter.on('hello/+', function(message, cb) {
  // will not be called
  console.log(message)
  cb()
})

emitter.emit({ topic: 'hello/my/world', something: 'more' })
emitter.emit({ topic: 'hello//world', something: 'more' })
```

The wildcard character `+` matches one word:

```js
const mq = require('mqemitter')
const emitter = mq({ matchEmptyLevels: true })

emitter.on('hello/+/world', function(message, cb) {
  // will capture { topic: 'hello/my/world', 'something': 'more' }
  // and capture { topic: 'hello//world', 'something': 'more' }
  console.log(message)
  cb()
})

emitter.on('hello/+', function(message, cb) {
  // will not be called
  console.log(message)
  cb()
})

emitter.emit({ topic: 'hello/my/world', something: 'more' })
emitter.emit({ topic: 'hello//world', something: 'more' })
```

The wildcard character `#` matches zero or more words:

```js
const mq = require('mqemitter')
const emitter = mq()

emitter.on('hello/#', function(message, cb) {
  // this will print { topic: 'hello/my/world', 'something': 'more' }
  console.log(message)
  cb()
})

emitter.on('#', function(message, cb) {
  // this will print { topic: 'hello/my/world', 'something': 'more' }
  console.log(message)
  cb()
})

emitter.on('hello/my/world/#', function(message, cb) {
  // this will print { topic: 'hello/my/world', 'something': 'more' }
  console.log(message)
  cb()
})

emitter.emit({ topic: 'hello/my/world', something: 'more' })
```

Of course, you can mix `#` and `+` in the same subscription.

## LICENSE

MIT

[mqemitter-redis]: https://www.npmjs.com/mqemitter-redis
[mqemitter-mongodb]: https://www.npmjs.com/mqemitter-mongodb
[mqemitter-child-process]: https://www.npmjs.com/mqemitter-child-process
[mqemitter-cs]: https://www.npmjs.com/mqemitter-cs
[mqemitter-p2p]: https://www.npmjs.com/mqemitter-p2p
[mqemitter-aerospike]: https://www.npmjs.com/mqemitter-aerospike
