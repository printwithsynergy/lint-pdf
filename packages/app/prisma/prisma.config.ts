import path from 'node:path'

const config = {
  schema: path.join(__dirname, 'prisma/schema.prisma'),
  datasource: {
    provider: 'postgresql',
    url: process.env.DATABASE_URL,
    directUrl: process.env.DIRECT_URL,
  },
}

export default config
