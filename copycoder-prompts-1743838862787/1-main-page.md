Set up the frontend according to the following prompt:
  <frontend-prompt>
  Create detailed components with these requirements:
  1. Use 'use client' directive for client-side components
  2. Make sure to concatenate strings correctly using backslash
  3. Style with Tailwind CSS utility classes for responsive design
  4. Use Lucide React for icons (from lucide-react package). Do NOT use other UI libraries unless requested
  5. Use stock photos from picsum.photos where appropriate, only valid URLs you know exist
  6. Configure next.config.js image remotePatterns to enable stock photos from picsum.photos
  7. Create root layout.tsx page that wraps necessary navigation items to all pages
  8. MUST implement the navigation elements items in their rightful place i.e. Left sidebar, Top header
  9. Accurately implement necessary grid layouts
  10. Follow proper import practices:
     - Use @/ path aliases
     - Keep component imports organized
     - Update current src/app/page.tsx with new comprehensive code
     - Don't forget root route (page.tsx) handling
     - You MUST complete the entire prompt before stopping
  </frontend-prompt>

  <summary_title>
Document Management System Dashboard with Search and Status Tracking
</summary_title>

<image_analysis>
1. Navigation Elements:
- Primary navigation: Compose, INCOMING, OUTGOING, MAINTENANCE, REPORTS, USER MANAGEMENT, MY ACCOUNT
- Left sidebar navigation with icon-based menu items
- Top header bar with system title "Document Management System"
- User profile section in top-right with notifications (1) and user avatar
- Search bar centered with filter options (All, Priority, Urgent, Usual)

2. Layout Components:
- Header height: ~60px
- Left sidebar width: ~200px
- Main content area: Flexible width
- Status cards: 4 equal-width containers
- Data table: Full width with responsive columns

3. Content Sections:
- Status Overview Cards:
  * All Incoming Docs (4)
  * Pending Docs (3)
  * Received Docs (1)
  * Ended Docs (0)
- Document List Table with columns:
  * Doc. Code
  * Sender
  * Details
  * Required Action
  * Date of Letter
  * Status
  * Action

4. Interactive Controls:
- Search bar with text input
- Filter toggles (All, Priority, Urgent, Usual)
- View buttons in table rows
- Status indicators (Pending, Received)
- Clickable document codes

5. Colors:
- Primary Blue: #2196F3 (All Incoming)
- Warning Yellow: #FFC107 (Pending)
- Success Green: #4CAF50 (Received)
- Danger Red: #F44336 (Ended)
- Text Dark: #263238
- Background: #FFFFFF
- Sidebar Dark: #1B2834

6. Grid/Layout Structure:
- 12-column grid system
- Status cards: 4-column layout
- Table: Responsive full-width
- Sidebar: Fixed width
- Content: Fluid width with padding
</image_analysis>

<development_planning>
1. Project Structure:
```
src/
├── components/
│   ├── layout/
│   │   ├── Header
│   │   ├── Sidebar
│   │   └── MainContent
│   ├── features/
│   │   ├── StatusCards
│   │   ├── DocumentTable
│   │   └── SearchFilters
│   └── shared/
├── assets/
├── styles/
├── hooks/
└── utils/
```

2. Key Features:
- Document status tracking
- Search functionality with filters
- Real-time notifications
- Document action management
- Status-based filtering
- User authentication

3. State Management:
```typescript
interface AppState {
  documents: {
    items: Document[];
    loading: boolean;
    filters: FilterOptions;
    search: string;
  };
  user: {
    profile: UserProfile;
    notifications: Notification[];
    preferences: UserPreferences;
  };
  ui: {
    sidebarOpen: boolean;
    activeTab: string;
    selectedFilters: string[];
  };
}
```

4. Component Architecture:
- App (Root)
  - Layout
    - Header
    - Sidebar
    - MainContent
      - StatusCards
      - SearchFilters
      - DocumentTable

5. Responsive Breakpoints:
```scss
$breakpoints: (
  'sm': 576px,
  'md': 768px,
  'lg': 992px,
  'xl': 1200px,
  'xxl': 1400px
);
```
</development_planning>