/**
 * Prisma 7 Configuration
 *
 * Handles split schema files and proper provider configuration for Prisma 7.6.0
 */

import type { PrismaConfig } from '@prisma/client';

const config: PrismaConfig = {
  // For split schema files, specify the main schema file
  schema: './prisma/schema.prisma',

  // Provider configuration for PostgreSQL
  datasource: {
    provider: 'postgresql',
    url: {
      fromEnvVar: 'DATABASE_URL',
    },
    directUrl: {
      fromEnvVar: 'DIRECT_URL',
    },
  },
};

export default config;
