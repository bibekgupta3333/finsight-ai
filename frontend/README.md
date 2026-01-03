# FinSight AI - Frontend

Next.js 14 frontend for the FinSight AI fraud detection system with multi-agent reasoning patterns.

## Stack

- **Framework:** Next.js 14 with App Router
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **UI Components:** shadcn/ui (Radix UI + Tailwind)
- **Icons:** lucide-react
- **HTTP Client:** Axios
- **File Upload:** react-dropzone
- **Charts:** Recharts
- **Date Utilities:** date-fns

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or pnpm
- Backend API running on `localhost:8000`

### Installation

```bash
cd frontend
npm install
```

### Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development

```bash
npm run dev

Frontend will be available at [http://localhost:3000](http://localhost:3000)

### Build

```bash
npm run build
npm start
```

## Features Implemented

### ✅ Section 4.1: Next.js Application Setup
- [x] Next.js 14 with App Router
- [x] TypeScript configuration
- [x] Tailwind CSS
- [x] shadcn/ui components (button, card, input, label, table, badge, progress, alert)
- [x] ESLint and Prettier

### ✅ Section 4.2: Core Pages (75% Complete)
- [x] **Landing Page** - Hero section showcasing platform capabilities
- [x] **Upload/Analyze Page** - CSV/PDF drag-and-drop with analysis
- [x] **Dashboard Page** - System monitoring and analytics
- [ ] Real-time monitoring (pending WebSocket integration)
- [ ] Insights & analytics (pending chart implementation)
- [ ] Settings page

### ✅ Section 4.5: API Integration (Core Complete)
- [x] API client service with Axios
- [x] TypeScript types from backend
- [x] Error handling and interceptors

## Testing Locally

1. **Start Backend:** `docker-compose up` (runs on http://localhost:8000)
2. **Start Frontend:** `npm run dev` (runs on http://localhost:3000)
3. **Upload Sample:** Use `public/sample-transactions.csv` on `/analyze` page

## License

MIT

