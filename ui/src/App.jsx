import { useState, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import LoadingScreen from './components/LoadingScreen'
import Dashboard from './components/Dashboard'
import Candidates from './components/Candidates'
import Personas from './components/Personas'
import BiasAudit from './components/BiasAudit'
import InterviewPacks from './components/InterviewPacks'
import Chat from './components/Chat'
import TopoBackground from './components/TopoBackground'

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [rankingData, setRankingData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingMsg, setLoadingMsg] = useState('Parsing resumes…')

  const onRankingComplete = useCallback((data) => {
    setRankingData(data)
    setActiveTab('dashboard')
  }, [])

  return (
    <div style={{ display: 'flex', width: '100%', minHeight: '100vh', background: 'var(--bg-primary)' }}>
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      <div style={{ marginLeft: 220, flex: 1, display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <Header activeTab={activeTab} rankingData={rankingData} />

        <main style={{
          flex: 1,
          padding: '40px 48px',
          overflowY: 'auto',
          position: 'relative',
        }}>
          <TopoBackground />
          <div style={{ position: 'relative', zIndex: 1 }}>
            {activeTab === 'dashboard'  && <Dashboard rankingData={rankingData} setLoading={setLoading} setLoadingMsg={setLoadingMsg} onRankingComplete={onRankingComplete} />}
            {activeTab === 'candidates' && <Candidates candidates={rankingData?.shortlist || []} />}
            {activeTab === 'personas'   && <Personas personas={rankingData?.personas || {}} />}
            {activeTab === 'bias'       && <BiasAudit report={rankingData?.bias_report || null} />}
            {activeTab === 'interviews' && <InterviewPacks />}
            {activeTab === 'chat'       && <Chat />}
          </div>
        </main>
      </div>

      {loading && <LoadingScreen message={loadingMsg} />}
    </div>
  )
}
