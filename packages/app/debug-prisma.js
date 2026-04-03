#!/usr/bin/env node

// Debug script to understand Prisma configuration issue
console.log('=== Prisma Debug Script ===');
console.log('Node version:', process.version);
console.log('Working directory:', process.cwd());
console.log('');

// Check environment variables
console.log('Environment variables:');
console.log('DATABASE_URL exists:', !!process.env.DATABASE_URL);
console.log('DIRECT_URL exists:', !!process.env.DIRECT_URL);
if (process.env.DATABASE_URL) {
  console.log('DATABASE_URL length:', process.env.DATABASE_URL.length);
  console.log('DATABASE_URL starts with postgresql:', process.env.DATABASE_URL.startsWith('postgresql://'));
}
if (process.env.DIRECT_URL) {
  console.log('DIRECT_URL length:', process.env.DIRECT_URL.length);
  console.log('DIRECT_URL starts with postgresql:', process.env.DIRECT_URL.startsWith('postgresql://'));
}
console.log('');

// Try to load prisma config
try {
  const fs = require('fs');
  const path = require('path');
  
  const configPath = path.join(process.cwd(), 'prisma.config.ts');
  console.log('Prisma config path:', configPath);
  console.log('Config exists:', fs.existsSync(configPath));
  
  if (fs.existsSync(configPath)) {
    const configContent = fs.readFileSync(configPath, 'utf8');
    console.log('Config content preview:');
    console.log(configContent.substring(0, 200) + '...');
  }
} catch (error) {
  console.error('Error reading config:', error.message);
}
console.log('');

// Try to load prisma schema
try {
  const fs = require('fs');
  const path = require('path');
  
  const schemaPath = path.join(process.cwd(), 'prisma/schema.prisma');
  console.log('Prisma schema path:', schemaPath);
  console.log('Schema exists:', fs.existsSync(schemaPath));
  
  if (fs.existsSync(schemaPath)) {
    const schemaContent = fs.readFileSync(schemaPath, 'utf8');
    console.log('Schema has datasource block:', schemaContent.includes('datasource'));
    console.log('Schema has url property:', schemaContent.includes('url'));
  }
} catch (error) {
  console.error('Error reading schema:', error.message);
}
console.log('');

// Try to run prisma command
try {
  const { execSync } = require('child_process');
  console.log('Running: npx prisma --version');
  const version = execSync('npx prisma --version', { encoding: 'utf8' });
  console.log('Prisma version:', version.trim());
} catch (error) {
  console.error('Error getting Prisma version:', error.message);
}
