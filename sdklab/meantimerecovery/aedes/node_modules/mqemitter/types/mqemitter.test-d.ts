import { expectError, expectType } from 'tsd';
import mqEmitter, { Message, MQEmitter } from './mqemitter';

expectType<MQEmitter>(mqEmitter());

expectType<MQEmitter>(mqEmitter({ concurrency: 200, matchEmptyLevels: true }));

expectType<MQEmitter>(
  mqEmitter({
    concurrency: 10,
    matchEmptyLevels: true,
    separator: '/',
    wildcardOne: '+',
    wildcardSome: '#',
  })
);

function listener(message: Message, done: () => void) {}

expectType<MQEmitter>(mqEmitter().on('topic', listener));

expectError(mqEmitter().emit(null));

expectType<void>(
  mqEmitter().emit({ topic: 'test', prop1: 'prop1', [Symbol.for('me')]: 42 })
);

expectType<void>(mqEmitter().emit({ topic: 'test', prop1: 'prop1' }, () => {}));

expectType<void>(mqEmitter().removeListener('topic', listener));

expectType<void>(mqEmitter().close(() => null));
