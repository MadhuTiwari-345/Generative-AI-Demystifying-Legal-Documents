import { NavBar } from '../components/navbar'
import 'bootstrap/dist/css/bootstrap.min.css';
import { Banner } from '../components/banner'
import { Skills } from '../components/skills'
import { Projects } from '../components/projects'
import { Contact } from '../components/contact'
import Footer from '../components/footer'

export default function demo() {
  return (
    <div className="App">
       <NavBar />
       <Banner />
       <Skills />
       <Projects />
       <Contact />
       <Footer />
    </div>
    
  )
}


