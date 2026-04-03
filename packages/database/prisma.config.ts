import path from 'node:path'
import { defineConfig } from 'prisma/config'

export default defineConfig({
  schema: path.join(__dirname, 'prisma/schema.prisma'),
  adapter: {
    provider: 'postgresql',
    url: process.env.DATABASE_URL,
  },
  directUrl: process.env.DIRECT_URL,
})
