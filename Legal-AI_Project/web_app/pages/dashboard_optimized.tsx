import { useEffect, useState } from 'react';
import { NavBar } from '../components/navbar';
import AccessDenied from '../components/access-denied';
import { useSession } from 'next-auth/react';

interface AnalysisResult {
  answer: string;
  confidence: string;
  sentiment: string;
  explanation: string;
}

const OptimizedDashboard: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [predefinedQuestions, setPredefinedQuestions] = useState<string[]>([]);
  const [selectedQuestion, setSelectedQuestion] = useState('');
  const [customQuestion, setCustomQuestion] = useState('');
  const [useCustomQuestion, setUseCustomQuestion] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [results, setResults] = useState<AnalysisResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [paraphrases, setParaphrases] = useState<string[]>([]);
  const { data: session, status } = useSession();

  useEffect(() => {
    fetchQuestions();
  }, []);

  const fetchQuestions = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5000/questions');
      const data = await response.json();
      setPredefinedQuestions(data);
      if (data.length > 0) {
        setSelectedQuestion(data[0]);
      }
    } catch (error) {
      console.error('Error fetching questions:', error);
      setError('Failed to load questions');
    }
  };

  const validateCustomQuestion = async (question: string) => {
    try {
      const response = await fetch('http://127.0.0.1:5000/validate-question', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      });
      const data = await response.json();
      return data;
    } catch (error) {
      return { valid: false, message: 'Error validating question' };
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setError('');
    }
  };

  const handleQuestionModeChange = (useCustom: boolean) => {
    setUseCustomQuestion(useCustom);
    setError('');
  };

  const handleCustomQuestionChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const question = e.target.value;
    setCustomQuestion(question);
    
    if (question.length > 5) {
      const validation = await validateCustomQuestion(question);
      if (!validation.valid) {
        setError(validation.message);
      } else {
        setError('');
      }
    }
  };

  const filteredQuestions = predefinedQuestions.filter(q =>
    q.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!selectedFile) {
      setError('Please select a file');
      return;
    }

    const question = useCustomQuestion ? customQuestion : selectedQuestion;
    if (!question.trim()) {
      setError('Please provide a question');
      return;
    }

    if (useCustomQuestion) {
      const validation = await validateCustomQuestion(question);
      if (!validation.valid) {
        setError(validation.message);
        return;
      }
    }

    setLoading(true);
    setError('');
    setResults([]);
    setParaphrases([]);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('question', question);

      const response = await fetch('http://127.0.0.1:5000/analyze', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Analysis failed');
      }

      const data = await response.json();
      setResults(data);
    } catch (error) {
      console.error('Analysis error:', error);
      setError('Failed to analyze document. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleExplainAnswer = async (answer: string) => {
    if (!answer || answer === 'No answer found in the document') return;

    try {
      const response = await fetch('http://127.0.0.1:5000/paraphrase', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: answer })
      });

      const data = await response.json();
      setParaphrases(data.paraphrases || []);
    } catch (error) {
      console.error('Paraphrase error:', error);
      setError('Failed to generate explanations');
    }
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment.toLowerCase()) {
      case 'positive': return '#4CAF50';
      case 'negative': return '#f44336';
      default: return '#757575';
    }
  };

  if (status === "unauthenticated") {
    return <AccessDenied />;
  }

  return (
    <>
      <div className='titre'>
        <div className='first-word'>Legal AI Analysis:</div>
        <div className='complete-phrase'>
          <span>Advanced Document Q&A with Custom Questions</span>
        </div>
      </div>

      <div className='dashboard'>
        <form onSubmit={handleSubmit} encType="multipart/form-data">
          {/* File Upload */}
          <label htmlFor="file-upload" className="drop-container">
            <span className="drop-title">
              {selectedFile ? selectedFile.name : 'Drop files here or click to browse'}
            </span>
            <input
              id="file-upload"
              type="file"
              className='file-upload'
              onChange={handleFileChange}
              accept=".pdf,.txt,.doc,.docx"
              required
            />
          </label>

          {/* Question Mode Selection */}
          <div className="question-mode-selector">
            <label>
              <input
                type="radio"
                checked={!useCustomQuestion}
                onChange={() => handleQuestionModeChange(false)}
              />
              Use Predefined Questions
            </label>
            <label>
              <input
                type="radio"
                checked={useCustomQuestion}
                onChange={() => handleQuestionModeChange(true)}
              />
              Ask Custom Question
            </label>
          </div>

          {/* Predefined Questions */}
          {!useCustomQuestion && (
            <div className="predefined-questions">
              <input
                type="text"
                placeholder="Search questions..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="search-box"
              />
              <select
                value={selectedQuestion}
                onChange={(e) => setSelectedQuestion(e.target.value)}
                className="select-box"
                required={!useCustomQuestion}
              >
                {filteredQuestions.map((question, index) => (
                  <option key={index} value={question}>
                    {question}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Custom Question Input */}
          {useCustomQuestion && (
            <div className="custom-question">
              <input
                type="text"
                placeholder="Enter your question (e.g., What are the payment terms?)"
                value={customQuestion}
                onChange={handleCustomQuestionChange}
                className="custom-question-input"
                required={useCustomQuestion}
                maxLength={200}
              />
              <small className="question-help">
                Ask specific questions about the document content. Use question words like "what", "who", "when", etc.
              </small>
            </div>
          )}

          {error && <div className="error-message">{error}</div>}

          <button
            type="submit"
            className="custom-btn btn-8"
            disabled={loading}
          >
            {loading ? 'Analyzing...' : 'Analyze Document'}
          </button>
        </form>

        {/* Results Display */}
        {results.length > 0 && (
          <div className="results-container">
            <div className="code-container">
              <section className="augs bg" data-augmented-ui>
                <input className="title" value="Analysis Results" readOnly />
                <div className="code highcontrast-dark">
                  {results.map((result, index) => (
                    <div key={index} className="result-item">
                      <div className="result-header">
                        <span className="result-number">Answer {index + 1}</span>
                        <span className="confidence">Confidence: {result.confidence}</span>
                        <span
                          className="sentiment"
                          style={{ color: getSentimentColor(result.sentiment) }}
                        >
                          {result.sentiment}
                        </span>
                      </div>
                      <div className="result-answer">{result.answer}</div>
                      <div className="result-explanation">{result.explanation}</div>
                      {result.answer !== 'No answer found in the document' && (
                        <button
                          onClick={() => handleExplainAnswer(result.answer)}
                          className="explain-btn"
                        >
                          Explain This Answer
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </div>
        )}

        {/* Paraphrases Display */}
        {paraphrases.length > 0 && (
          <div className="paraphrases-container">
            <h3>Alternative Explanations:</h3>
            {paraphrases.map((paraphrase, index) => (
              <div key={index} className="paraphrase-item">
                <span className="paraphrase-number">{index + 1}.</span>
                <span className="paraphrase-text">{paraphrase}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <style jsx>{`
        .dashboard {
          max-width: 1200px;
          margin: 0 auto;
          padding: 20px;
        }

        .drop-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 40px;
          border: 2px dashed #ccc;
          border-radius: 8px;
          margin-bottom: 20px;
          cursor: pointer;
          transition: border-color 0.3s;
        }

        .drop-container:hover {
          border-color: #007bff;
        }

        .file-upload {
          margin-top: 10px;
        }

        .question-mode-selector {
          display: flex;
          gap: 20px;
          margin-bottom: 20px;
        }

        .question-mode-selector label {
          display: flex;
          align-items: center;
          gap: 8px;
          cursor: pointer;
        }

        .search-box {
          width: 100%;
          padding: 10px;
          margin-bottom: 10px;
          border: 1px solid #ddd;
          border-radius: 4px;
        }

        .select-box {
          width: 100%;
          padding: 10px;
          margin-bottom: 20px;
          border: 1px solid #ddd;
          border-radius: 4px;
        }

        .custom-question-input {
          width: 100%;
          padding: 12px;
          margin-bottom: 8px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 16px;
        }

        .question-help {
          color: #666;
          font-size: 12px;
          margin-bottom: 20px;
          display: block;
        }

        .error-message {
          color: #f44336;
          margin-bottom: 15px;
          padding: 10px;
          background-color: #ffebee;
          border-radius: 4px;
        }

        .custom-btn {
          background: linear-gradient(45deg, #007bff, #0056b3);
          color: white;
          border: none;
          padding: 12px 24px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 16px;
          transition: all 0.3s;
        }

        .custom-btn:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 4px 8px rgba(0,123,255,0.3);
        }

        .custom-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .results-container {
          margin-top: 30px;
        }

        .result-item {
          margin-bottom: 20px;
          padding: 15px;
          border: 1px solid #eee;
          border-radius: 8px;
          background: #f9f9f9;
        }

        .result-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 10px;
          font-weight: bold;
        }

        .result-answer {
          margin-bottom: 10px;
          line-height: 1.6;
        }

        .result-explanation {
          font-size: 14px;
          color: #666;
          margin-bottom: 10px;
        }

        .explain-btn {
          background: #28a745;
          color: white;
          border: none;
          padding: 6px 12px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 14px;
        }

        .paraphrases-container {
          margin-top: 20px;
          padding: 20px;
          background: #f0f8ff;
          border-radius: 8px;
        }

        .paraphrase-item {
          margin-bottom: 10px;
          padding: 10px;
          background: white;
          border-radius: 4px;
        }

        .paraphrase-number {
          font-weight: bold;
          margin-right: 10px;
        }
      `}</style>
    </>
  );
};

export default OptimizedDashboard;