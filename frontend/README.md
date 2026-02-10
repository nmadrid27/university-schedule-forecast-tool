# SCAD FOUN Forecasting Tool - Frontend

Modern React frontend for the SCAD FOUN Enrollment Forecasting Tool. Built with Next.js, React 19, and Tailwind CSS 4.

## Getting Started

### Quick Start

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the app.

### One-Click Launch

From the project root, you can use the launcher:

```bash
./Forecast_Tool_Launcher.command
```

## Troubleshooting

### Turbopack Database Error

If you see "Failed to open database" when starting:

```bash
# Clean the build cache
rm -rf .next

# Use webpack instead of turbopack
NEXT_PRIVATE_WEBPACK=1 npm run dev
```

### Port Already in Use

```bash
# Kill the process on port 3000
lsof -ti:3000 | xargs kill -9

# Or use a different port
PORT=3001 npm run dev
```

## Tech Stack

- **Framework**: Next.js 16.1.6 with React 19
- **Styling**: Tailwind CSS 4
- **UI Components**: Radix UI primitives
- **Icons**: Lucide React
- **TypeScript**: 5.x

## Development

### Project Structure

```
frontend/
├── src/
│   ├── app/          # Next.js app directory
│   ├── components/   # React components
│   ├── hooks/        # Custom React hooks
│   └── lib/          # Utility functions
├── public/           # Static assets
└── package.json      # Dependencies
```

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## Features

- Real-time parameter adjustments
- CSV/Excel data upload
- Interactive forecasting configuration
- Results export
- Responsive design
- Dark mode support

## Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [Tailwind CSS](https://tailwindcss.com)
- [Radix UI](https://www.radix-ui.com)

## Parent Project

This is the frontend for the SCAD FOUN Enrollment Forecasting Tool. See the [main README](../README.md) for complete project documentation.
