export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-4xl md:text-6xl font-bold text-slate-900 dark:text-white mb-6">
            ConstructionRAG
          </h1>
          <p className="text-xl md:text-2xl text-slate-600 dark:text-slate-300 mb-8">
            AI-powered construction document processing and Q&A system
          </p>
          <div className="bg-white dark:bg-slate-800 rounded-lg shadow-lg p-8">
            <h2 className="text-2xl font-semibold text-slate-900 dark:text-white mb-4">
              Welcome to ConstructionRAG
            </h2>
            <p className="text-slate-600 dark:text-slate-300">
              Your DeepWiki for Construction Sites - automatically process construction documents 
              and enable intelligent Q&A about project requirements, timelines, and specifications.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}