import {useState} from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Home(){
  const [text, setText] = useState('')
  const [taskId, setTaskId] = useState(null)
  const [status, setStatus] = useState(null)
  const [progress, setProgress] = useState(null)
  const [result, setResult] = useState(null)

  async function submit(e){
    e.preventDefault()
    setStatus('PENDING')
    setResult(null)
    setProgress(null)
    
    const res = await fetch(`${API_BASE}/submit`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text}),
    })
    const body = await res.json()
    setTaskId(body.task_id)
    pollStatus(body.task_id)
  }

  async function pollStatus(id){
    const url = `${API_BASE}/status/${id}`
    const iv = setInterval(async ()=>{
      const r = await fetch(url)
      const j = await r.json()
      // backend returns `state` and optional `meta` with progress
      setStatus(j.state)
      if(j.meta){
        if(typeof j.meta.percent === 'number'){
          setProgress(j.meta.percent)
        } else if(j.meta.current && j.meta.total){
          setProgress(Math.round((j.meta.current / j.meta.total) * 100))
        }
      }
      if(j.state === 'SUCCESS'){
        setResult(j.result)
        clearInterval(iv)
      }
      if(j.state === 'FAILURE'){
        setResult({error: j.error})
        clearInterval(iv)
      }
    }, 1000)
  }

  return (
    <div style={{maxWidth:800, margin:'40px auto', fontFamily:'Arial'}}>
      <h1>Text processing demo (Celery)</h1>
      <form onSubmit={submit}>
        <textarea value={text} onChange={e=>setText(e.target.value)} rows={6} style={{width:'100%'}} />
        <div style={{marginTop:8}}>
          <button type="submit">Submit</button>
        </div>
      </form>

      {taskId && <div style={{marginTop:20}}>
        <strong>Task:</strong> {taskId}<br/>
        <strong>Status:</strong> {status}
        {progress !== null && <div style={{marginTop:8}}>
          <strong>Progress:</strong> {progress}%
        </div>}
      </div>}

      {result && <div style={{marginTop:20}}>
        <h3>Result</h3>
        {result.elapsed_time !== undefined && (
          <div style={{marginBottom:12, padding:8, backgroundColor:'#e3f2fd', borderRadius:4, border:'1px solid #2196f3'}}>
            <strong>Total Time (Request to Result):</strong> {result.elapsed_time} seconds
            <div style={{fontSize:'0.9em', color:'#666', marginTop:4}}>
              Includes queue wait time and processing time
            </div>
          </div>
        )}
        <pre>{JSON.stringify(result, null, 2)}</pre>
      </div>}
    </div>
  )
}


