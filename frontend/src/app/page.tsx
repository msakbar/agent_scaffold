import Chat from '@/components/Chat';

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">Chat AI</h1>
          <p className="text-gray-600">Powered by Google Agent Development Kit</p>
        </div>
      </header>
      
      <main className="h-[calc(100vh-120px)]">
        <Chat />
      </main>
    </div>
  );
}
