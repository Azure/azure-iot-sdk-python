export interface ConnectionDetails {
  ipAddress: string
  port: number
  ipFamily: number
  serverIpAddress: string
  isWebsocket: boolean
  isProxy: number
  data?: Buffer
}

export type ProtocolDecoder = (client: Object, buffer: Buffer) => ConnectionDetails | null
