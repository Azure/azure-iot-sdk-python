/* eslint no-unused-vars: 0 */
/* eslint no-undef: 0 */
/* eslint space-infix-ops: 0 */

/// <reference types="node" />

import { Packet as IPacket } from 'mqtt-packet'

declare namespace aedes {

  type AedesPacket = IPacket & {
    brokerId: string
    brokerCounter: number
  }

  function Packet(object?: AedesPacket) : aedes.AedesPacket
}

export = aedes
