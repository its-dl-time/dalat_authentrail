# Dalat Authentrail Frontend

Angular-based frontend for Place Risk Intelligence application.

## Getting Started

### Prerequisites
- Node.js 18+ and npm
- Angular CLI 18+

### Installation

```bash
cd frontend
npm install
```

### Development Server

```bash
npm run dev
# or
ng serve --open
```

Navigate to `http://localhost:4200/`. The application will automatically reload if you change any of the source files.

### Build

```bash
npm run build
# or
ng build
```

The build artifacts will be stored in the `dist/` directory.

### Code Scaffolding

```bash
ng generate component component-name
ng generate service service-name
ng generate module module-name
```

### Running Unit Tests

```bash
ng test
```

### Linting

```bash
ng lint
```

## Project Structure

```
src/
├── app/
│   ├── core/
│   │   ├── services/
│   │   ├── guards/
│   │   ├── interceptors/
│   │   └── models/
│   ├── features/
│   │   ├── home/
│   │   ├── search/
│   │   ├── place-detail/
│   │   ├── compare/
│   │   ├── community/
│   │   ├── ai-planner/
│   │   ├── profile/
│   │   └── ranking/
│   ├── shared/
│   │   ├── components/
│   │   ├── pipes/
│   │   ├── directives/
│   │   └── models/
│   └── auth/
├── assets/
│   ├── images/
│   ├── icons/
│   └── data/
├── styles/
│   ├── _colors.scss
│   ├── _typography.scss
│   └── _components.scss
└── environments/
    ├── environment.ts
    └── environment.prod.ts
```

## Features Implemented

- [ ] Phase 1: Place Risk Intelligence
  - [ ] Home/Landing Page
  - [ ] Search Results Page
  - [ ] Place Detail Page
  - [ ] Compare Page
- [ ] Phase 2: Real-time Community
  - [ ] Ask Question Panel
  - [ ] Answer Feed
  - [ ] Verification Labels
  - [ ] User Ranking System
- [ ] Phase 3: AI Travel Agent
  - [ ] AI Planner Chat
  - [ ] Trip Timeline
  - [ ] Real-time Alerts
  - [ ] Saved Trips
- [ ] Authentication
  - [ ] Login/Register
  - [ ] User Profile
  - [ ] Account Settings

## Styling

The project uses SCSS with a custom color palette inspired by Coiny - Dalat Authentrail. See `src/styles/` for global styles and component-specific styles.

## API Integration

API calls are managed through services in `src/app/core/services/`. Environment-specific URLs are configured in `src/environments/`.

## Further Help

To get more help on the Angular CLI use `ng help` or go check out the [Angular Documentation](https://angular.io/docs).
