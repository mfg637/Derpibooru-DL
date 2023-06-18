import React from 'react';
import { createRoot } from 'react-dom/client';

import { useState } from 'react';
import { useEffect } from 'react';

const domContainer = document.querySelector('#react-app-root');
const react_root = createRoot(domContainer);

function LoadingSpinner(){
  return (
    <div className="loading-spinner">
      <div></div>
      <div></div>
      <div></div>
      <div></div>
      <div></div>
      <div></div>
      <div></div>
      <div></div>
    </div>
  )
}

function Task(props) {
  return (
    <div className="task">
      <div className="icon">{props.is_done?"✔️":<LoadingSpinner />}</div>
      <div>{props.title}</div>
    </div>
  );
}

function TaskList() {
  const [processingStatus, setProcessingStatus] = useState([]);

  function updateStatus(){
  fetch("/get_status.json").then(
    (response) => {
      if (response.ok) {
        response.json().then(
          (data) => {
            setProcessingStatus(data);
          }
        )
      } else {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
    });
  }

  useEffect(() => {
    const timeoutFunction = setInterval(updateStatus, 500)
    return () => clearInterval(timeoutFunction);
  }, []);

  return (
    <div>
      {processingStatus.map((value, index) => <Task key={index} {...value}/>)}
    </div>
  )
}

const app = <TaskList />;
react_root.render(app);