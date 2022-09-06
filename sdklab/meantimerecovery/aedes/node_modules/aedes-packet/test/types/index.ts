/* eslint no-unused-vars: 0 */
/* eslint no-undef: 0 */

import { Packet } from '../../packet'

var p = Packet()
p = Packet({
  cmd: 'publish',
  topic: 'hello',
  payload: Buffer.from('world'),
  qos: 0,
  dup: false,
  retain: false,
  brokerId: 'afds8f',
  brokerCounter: 10
})
p = Packet({
  cmd: 'pingresp',
  brokerId: 'ab7d9',
  brokerCounter: 3
})
