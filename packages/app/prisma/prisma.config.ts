const config = {
  datasource: {
    provider: 'postgresql',
    url: {
      fromEnvVar: 'DATABASE_URL',
    },
    directUrl: {
      fromEnvVar: 'DIRECT_URL',
    },
  },
}

export default config
