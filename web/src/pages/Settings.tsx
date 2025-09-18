import React, { useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Divider,
  FormControl,
  FormControlLabel,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  SelectChangeEvent,
  Switch,
  TextField,
  Typography,
  Alert,
  Snackbar,
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';

const Settings: React.FC = () => {
  const { user } = useAuth();
  const [themeMode, setThemeMode] = useState<string>('dark');
  const [notificationsEnabled, setNotificationsEnabled] = useState<boolean>(true);
  const [detectionThreshold, setDetectionThreshold] = useState<number>(0.5);
  const [savedSuccess, setSavedSuccess] = useState<boolean>(false);

  const handleThemeModeChange = (event: SelectChangeEvent) => {
    setThemeMode(event.target.value);
  };

  const handleNotificationsChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setNotificationsEnabled(event.target.checked);
  };

  const handleDetectionThresholdChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseFloat(event.target.value);
    if (!isNaN(value) && value >= 0 && value <= 1) {
      setDetectionThreshold(value);
    }
  };

  const handleSaveSettings = () => {
    // Aqui seria implementada a lógica para salvar as configurações no backend
    console.log('Configurações salvas:', {
      themeMode,
      notificationsEnabled,
      detectionThreshold,
    });
    
    // Mostrar mensagem de sucesso
    setSavedSuccess(true);
  };

  const handleCloseSnackbar = () => {
    setSavedSuccess(false);
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Typography variant="h4" gutterBottom>
        Configurações
      </Typography>

      <Grid container spacing={3}>
        <Grid xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Perfil do Usuário
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="body1">
                  <strong>Nome de Usuário:</strong> {user?.username}
                </Typography>
              </Box>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="body1">
                  <strong>Email:</strong> {user?.email}
                </Typography>
              </Box>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="body1">
                  <strong>Função:</strong> {user?.role}
                </Typography>
              </Box>
              
              <Button variant="outlined" sx={{ mt: 2 }}>
                Alterar Senha
              </Button>
            </CardContent>
          </Card>
        </Grid>

        <Grid xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Preferências da Interface
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel id="theme-mode-label">Tema</InputLabel>
                <Select
                  labelId="theme-mode-label"
                  id="theme-mode"
                  value={themeMode}
                  label="Tema"
                  onChange={handleThemeModeChange}
                >
                  <MenuItem value="light">Claro</MenuItem>
                  <MenuItem value="dark">Escuro</MenuItem>
                  <MenuItem value="system">Sistema</MenuItem>
                </Select>
              </FormControl>
              
              <FormControlLabel
                control={
                  <Switch
                    checked={notificationsEnabled}
                    onChange={handleNotificationsChange}
                  />
                }
                label="Ativar notificações"
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Configurações de Detecção
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <Grid container spacing={2}>
                <Grid xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Limite de Confiança (0-1)"
                    type="number"
                    inputProps={{ min: 0, max: 1, step: 0.01 }}
                    value={detectionThreshold}
                    onChange={handleDetectionThresholdChange}
                    helperText="Valores menores detectam mais objetos, mas com mais falsos positivos"
                  />
                </Grid>
              </Grid>
              
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                Estas configurações afetam como o sistema detecta objetos nas câmeras.
                Ajuste conforme necessário para melhorar a precisão da detecção.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
        <Button variant="contained" onClick={handleSaveSettings}>
          Salvar Configurações
        </Button>
      </Box>

      <Snackbar
        open={savedSuccess}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseSnackbar} severity="success" sx={{ width: '100%' }}>
          Configurações salvas com sucesso!
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Settings;
