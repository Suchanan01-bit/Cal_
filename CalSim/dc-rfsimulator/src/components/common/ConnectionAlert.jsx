/**
 * ConnectionAlert.jsx
 * Toast notification for connection status
 */

import { useState, useEffect, useCallback } from 'react';
import './ConnectionAlert.css';

function ConnectionAlert({ alerts, onDismiss }) {
    return (
        <div className="connection-alerts-container">
            {alerts.map((alert) => (
                <AlertItem
                    key={alert.id}
                    alert={alert}
                    onDismiss={() => onDismiss(alert.id)}
                />
            ))}
        </div>
    );
}

function AlertItem({ alert, onDismiss }) {
    const [isExiting, setIsExiting] = useState(false);

    useEffect(() => {
        // Auto dismiss after 4 seconds
        const timer = setTimeout(() => {
            setIsExiting(true);
            setTimeout(onDismiss, 300);
        }, 4000);

        return () => clearTimeout(timer);
    }, [onDismiss]);

    const handleClick = useCallback(() => {
        setIsExiting(true);
        setTimeout(onDismiss, 300);
    }, [onDismiss]);

    const getIcon = () => {
        switch (alert.type) {
            case 'success':
                return '✓';
            case 'error':
                return '✕';
            case 'warning':
                return '⚠';
            case 'info':
            default:
                return 'ℹ';
        }
    };

    return (
        <div
            className={`connection-alert ${alert.type} ${isExiting ? 'exiting' : ''}`}
            onClick={handleClick}
        >
            <div className="alert-icon">{getIcon()}</div>
            <div className="alert-content">
                <div className="alert-title">{alert.title}</div>
                <div className="alert-message">{alert.message}</div>
            </div>
            <div className="alert-close">×</div>
        </div>
    );
}

export default ConnectionAlert;
