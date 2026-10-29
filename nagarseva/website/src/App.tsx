import CivicWorkspace from './civic/CivicWorkspace'

// Active application uses the isolated synthetic adapter. Archived source modules
// and their SQLite records are preserved, but no historical layer is loaded here.
export default function App() { return <CivicWorkspace /> }
