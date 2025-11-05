import { useEffect, useState } from 'react';
import { NavBar } from '../components/navbar';
import axios from 'axios';
import AccessDenied from '../components/access-denied';
import { useSession } from 'next-auth/react';

const FileUpload: React.FC = () => {
  const [selectedResponse, setSelectedResponse] = useState<string>('');
  const [questions, setQuestions] = useState([]);
  const [selectedQuestion, setSelectedQuestion] = useState('');
  const { data: session, status } = useSession();
  useEffect(() => {
    fetchQuestions();
  }, []);

  const fetchQuestions = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5000/questionsshort'); // Replace with your Flask API endpoint
      const data = await response.json();
      console.log(data);
      setQuestions(data);
    } catch (error) {
      console.log('Error fetching questions:', error);
    }
  };
  const handleQuestionSelect = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedQuestion(event.target.value);
  };
  const handleFormSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    
    // Show loading state
    const textarea = document.getElementById('response') as HTMLTextAreaElement;
    textarea.value = 'Processing... Please wait.';
    
    try {
      const response = await fetch('http://127.0.0.1:5000/contracts/', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.error) {
        textarea.value = `Error: ${data.error}`;
        return;
      }
      
      if (Array.isArray(data) && data.length > 0) {
        setSelectedResponse(data[0].answer);
        
        const textareaContent = data
          .map(
            (res: { answer: any; probability: any; analyse: any }, index: number) =>
              `Answer ${index + 1}: ${res.answer} (${res.probability}) (${res.analyse})`
          )
          .join('\n');
        
        textarea.value = textareaContent;
  
        // Clear previous explanation
        document.getElementById('explanation')!.innerHTML = '';
      } else {
        textarea.value = 'No answers found in the document.';
      }
      
    } catch (error) {
      console.error('Error:', error);
      textarea.value = `Error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`;
    }
  };
  
  
  

  const handleExplanationClick = async () => {
    if (!selectedResponse || selectedResponse.trim() === '') {
      alert('Please generate a response first.');
      return;
    }
    
    const explanationDiv = document.getElementById('explanation')!;
    explanationDiv.innerHTML = '<p>Generating explanation... Please wait.</p>';
    
    try {
      const encodedSelectedResponse = encodeURIComponent(selectedResponse);
      const apiUrl = `http://127.0.0.1:5000/contracts/paraphrase/${encodedSelectedResponse}`;
      
      const response = await fetch(apiUrl);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.error) {
        explanationDiv.innerHTML = `<p>Error: ${data.error}</p>`;
        return;
      }
      
      if (Array.isArray(data)) {
        const htmlContent = data
          .map((element: string) => `<p>${element}</p>`)
          .join('');
        explanationDiv.innerHTML = htmlContent;
      } else {
        explanationDiv.innerHTML = '<p>No explanation available.</p>';
      }
    } catch (error) {
      console.error('Error:', error);
      explanationDiv.innerHTML = `<p>Error: ${error instanceof Error ? error.message : 'Unknown error occurred'}</p>`;
    }
  };
  if(status === "unauthenticated") {
    return (
        <>{status}
        <AccessDenied /></>
    )
}
  return (
    < >
    
        <div className='titre'>
            <div className='first-word'>Contract Q&A:</div> 
            <div className='complete-phrase'> 
            <span>Unlocking Answers to Vital Questions</span>
            </div>
        </div>
    <div className='dashboard'>

      <form onSubmit={handleFormSubmit} encType="multipart/form-data">
        {/* <input type="file" name="file" /> */}
        <label htmlFor="images" className="drop-container">
            <span className="drop-title">Drop files here</span>
            or
            <input type="file" className='file-upload'   name="file"  required />
            </label>
        <select name="question" className="select-box" >
          {/* <option value="What is the contract name?">
            What is the contract name?
          </option>
          <option value="Who are the parties that signed the contract?">
            Who are the parties that signed the contract?
          </option>
          <option value="What is the agreement date of the contract?">
            What is the agreement date of the contract?
          </option> */}
          {questions && questions.map((question, index) => (
                <option key={index} value={question}>
                    {question}
                </option>
                ))}
        </select>
        <input  className="custom-btn btn-8" type="submit" value="Generate Response" />
      </form>
      {/* <div id="response"></div> */}
      <div className="code-container">
                
                <section className="augs bg" data-augmented-ui>
                <input className="title" value="Get Response" readOnly />
                    <div className="code highcontrast-dark">
                        
                            <textarea id="response" className="code-textarea" rows={10}   placeholder="Generate Response..." readOnly>

                            </textarea> 
                    </div>
                    
                    
                    
                </section>
        </div>
      <button className="custom-btn btn-9" onClick={handleExplanationClick}><span>Explain response</span></button>
      
      <div className="ccode highcontrast-dark" id="explanation"></div>
      <div className="ccode highcontrast-dark" id="analysis"></div>
    </div>
    </>
  );
};

export default FileUpload;
