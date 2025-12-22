/** @type {import('next').NextConfig} */
const nextConfig = {
    // Enable standalone output for Docker
    output: 'standalone',

    // Disable strict mode for development
    reactStrictMode: true,

    // Image optimization
    images: {
        domains: ['localhost'],
    },
}

module.exports = nextConfig
