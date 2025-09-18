import React, { useMemo } from 'react';
import { Box, Paper, Typography, Grid } from '@mui/material';
import { 
  Chart as ChartJS, 
  ArcElement, 
  Tooltip, 
  Legend, 
  CategoryScale,
  LinearScale,
  BarElement,
  Title
} from 'chart.js';
import { Pie, Bar } from 'react-chartjs-2';
import { Event } from '../services/eventService';

// Registrar os componentes do Chart.js
ChartJS.register(
  ArcElement, 
  Tooltip, 
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
  Title
);

// Cores para os diferentes tipos de eventos
const eventColors: Record<string, string> = {
  person: 'rgba(54, 162, 235, 0.8)',
  vehicle: 'rgba(255, 99, 132, 0.8)',
  motion: 'rgba(255, 206, 86, 0.8)',
  object: 'rgba(75, 192, 192, 0.8)',
  alert: 'rgba(153, 102, 255, 0.8)',
  system: 'rgba(255, 159, 64, 0.8)',
  // Cores de fallback para outros tipos
  default1: 'rgba(199, 199, 199, 0.8)',
  default2: 'rgba(83, 102, 255, 0.8)',
  default3: 'rgba(255, 99, 71, 0.8)',
};

interface EventTypeChartsProps {
  events: Event[];
}

const EventTypeCharts: React.FC<EventTypeChartsProps> = ({ events }) => {
  // Processar os dados para os gráficos
  const chartData = useMemo(() => {
    // Contagem de eventos por tipo
    const eventTypeCounts: Record<string, number> = {};
    
    events.forEach(event => {
      const eventType = event.event_type || 'unknown';
      eventTypeCounts[eventType] = (eventTypeCounts[eventType] || 0) + 1;
    });
    
    // Preparar dados para o gráfico de pizza
    const labels = Object.keys(eventTypeCounts);
    const data = Object.values(eventTypeCounts);
    
    // Atribuir cores para cada tipo de evento
    const backgroundColor = labels.map(type => {
      return eventColors[type.toLowerCase()] || 
        eventColors.default1 || 
        'rgba(128, 128, 128, 0.8)';
    });
    
    return {
      labels,
      data,
      backgroundColor
    };
  }, [events]);
  
  // Configuração do gráfico de pizza
  const pieChartData = {
    labels: chartData.labels,
    datasets: [
      {
        data: chartData.data,
        backgroundColor: chartData.backgroundColor,
        borderWidth: 1,
      },
    ],
  };
  
  // Configuração do gráfico de barras
  const barChartData = {
    labels: chartData.labels,
    datasets: [
      {
        label: 'Quantidade de Eventos',
        data: chartData.data,
        backgroundColor: chartData.backgroundColor,
        borderWidth: 1,
      },
    ],
  };
  
  const barChartOptions = {
    responsive: true,
    plugins: {
      legend: {
        display: false,
      },
      title: {
        display: true,
        text: 'Eventos por Tipo',
        color: '#FFFFFF',
      },
      tooltip: {
        callbacks: {
          label: function(context: any) {
            return `Quantidade de Eventos: ${context.raw}`;
          }
        }
      }
    },
    scales: {
      x: {
        ticks: {
          color: '#FFFFFF',
        },
        grid: {
          color: 'rgba(255, 255, 255, 0.1)',
        }
      },
      y: {
        ticks: {
          color: '#FFFFFF',
        },
        grid: {
          color: 'rgba(255, 255, 255, 0.1)',
        }
      }
    },
  };

  // Configuração do gráfico de pizza
  const pieChartOptions = {
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          color: '#FFFFFF',
          font: {
            size: 12
          }
        },
      },
      tooltip: {
        callbacks: {
          label: function(context: any) {
            return ` ${context.label}: ${context.raw} (${Math.round(context.parsed * 100) / 100}%)`;  
          }
        }
      }
    },
  };

  return (
    <Paper sx={{ p: 2, mb: 3, bgcolor: 'rgba(0, 0, 0, 0.2)', borderRadius: 2 }}>
      <Typography variant="h6" gutterBottom sx={{ color: '#FFFFFF' }}>
        Resumo de Eventos por Tipo
      </Typography>
      
      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Box sx={{ height: 300, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <Pie data={pieChartData} options={pieChartOptions} />
          </Box>
        </Grid>
        <Grid item xs={12} md={6}>
          <Box sx={{ height: 300, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <Bar data={barChartData} options={{ ...barChartOptions, maintainAspectRatio: false }} />
          </Box>
        </Grid>
      </Grid>
    </Paper>
  );
};

export default EventTypeCharts;
