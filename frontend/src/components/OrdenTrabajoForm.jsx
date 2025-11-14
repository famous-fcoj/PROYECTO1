import React, { useState, useRef } from 'react';
import { cargarExcel } from '../services/api';
import './OrdenTrabajoForm.css';

const OrdenTrabajoForm = () => {
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);
  
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validar tipo de archivo
    if (!file.name.match(/\.(xlsx|xls)$/)) {
      setError('Por favor, selecciona un archivo Excel (.xlsx o .xls)');
      return;
    }

    try {
      setUploading(true);
      setError(null);
      setResult(null);

      const response = await cargarExcel(file);
      setResult(response);
      
      // Limpiar input de archivo
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err) {
      setError(err.message || 'Error al cargar el archivo');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-container" style={{ padding: '20px' }}>
      <h2>Carga de Órdenes de Trabajo</h2>
      
      <div className="upload-section" style={{ marginTop: '20px' }}>
        <div className="file-input-container">
          <input
            type="file"
            onChange={handleFileUpload}
            accept=".xlsx,.xls"
            disabled={uploading}
            ref={fileInputRef}
            style={{ marginBottom: '10px' }}
          />
          
          {uploading && (
            <div className="loading-indicator">
              Cargando archivo...
            </div>
          )}
        </div>

        {error && (
          <div className="error-message" style={{ 
            color: 'red', 
            padding: '10px', 
            marginTop: '10px',
            backgroundColor: '#ffebee',
            borderRadius: '4px'
          }}>
            {error}
          </div>
        )}

        {result && (
          <div className="result-container" style={{
            marginTop: '20px',
            padding: '15px',
            backgroundColor: '#e8f5e9',
            borderRadius: '4px'
          }}>
            <h3>Resultado de la carga:</h3>
            <div>
              <p>✅ {result.registros_procesados} registros procesados exitosamente</p>
              
              {result.errores && result.errores.length > 0 && (
                <div>
                  <h4>Errores encontrados:</h4>
                  <ul style={{ maxHeight: '200px', overflowY: 'auto' }}>
                    {result.errores.map((error, index) => (
                      <li key={index} style={{ color: '#d32f2f' }}>
                        Fila {error.fila}: {error.error} (OT: {error.ot})
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        <div className="instructions" style={{ 
          marginTop: '20px', 
          padding: '15px',
          backgroundColor: '#e3f2fd',
          borderRadius: '4px'
        }}>
          <h4>Instrucciones:</h4>
          <ul>
            <li>El archivo debe ser formato Excel (.xlsx o .xls)</li>
            <li>Columnas requeridas:
              <ul>
                <li>Encargado</li>
                <li>Máquina</li>
                <li>Tipo de falla</li>
                <li>Fecha inicio</li>
              </ul>
            </li>
            <li>Columnas opcionales:
              <ul>
                <li>Fecha término</li>
                <li>DIAS</li>
                <li>PERSONAS</li>
                <li>HH</li>
                <li>Observación</li>
                <li>Mantención lograda</li>
              </ul>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default OrdenTrabajoForm;