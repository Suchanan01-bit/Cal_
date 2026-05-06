import { useState } from 'react';
import { useTasks } from '../../context/TaskContext';
import './TaskBox.css';

function TaskBox() {
    const { tasks, openTaskModal, removeTask } = useTasks();
    const [isExpanded, setIsExpanded] = useState(true);

    const completedTasksCount = tasks.filter(t => t.completed).length;

    return (
        <div className={`task-box ${isExpanded ? 'expanded' : 'collapsed'}`}>
            <div className="task-box-header" onClick={() => setIsExpanded(!isExpanded)}>
                <div className="task-box-title">
                    📋 Task List ({completedTasksCount}/{tasks.length})
                </div>
                <button className="task-box-toggle">
                    {isExpanded ? '▼' : '▲'}
                </button>
            </div>
            
            {isExpanded && (
                <div className="task-box-content">
                    {tasks.length === 0 ? (
                        <div className="no-tasks">No tasks defined.</div>
                    ) : (
                        <ul className="task-list">
                            {tasks.map(task => (
                                <li key={task.id} className={`task-item ${task.completed ? 'completed' : ''}`}>
                                    <div className="task-checkbox">
                                        {task.completed ? '✅' : '⏳'}
                                    </div>
                                    <div className="task-desc">
                                        {task.description}
                                    </div>
                                    <button 
                                        className="task-remove-btn" 
                                        onClick={(e) => { e.stopPropagation(); removeTask(task.id); }}
                                        title="Remove Task"
                                    >
                                        ×
                                    </button>
                                </li>
                            ))}
                        </ul>
                    )}
                    
                    <div className="task-box-footer">
                        <button className="add-task-btn" onClick={openTaskModal}>
                            + Custom Task
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

export default TaskBox;
