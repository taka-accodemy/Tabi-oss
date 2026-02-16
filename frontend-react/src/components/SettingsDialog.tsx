import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogDescription
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Database, Save, Loader2, Info, RotateCcw, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

interface SchemaItem {
  name: string;
  type: 'measure' | 'dimension';
  title: string;
  description: string;
  cube: string;
  polarity?: 'positive' | 'negative' | 'neutral';
}


interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  const { t, i18n } = useTranslation();
  const [schemaItems, setSchemaItems] = useState<SchemaItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [editedDescriptions, setEditedDescriptions] = useState<Record<string, string>>({});
  const [editedPolarity, setEditedPolarity] = useState<Record<string, 'positive' | 'negative' | 'neutral'>>({});
  const [activeTab, setActiveTab] = useState('schema');
  
  // Database Config State
  const [dbType, setDbType] = useState<'postgres' | 'bigquery' | 'iceberg'>('postgres');
  const [postgresConfig, setPostgresConfig] = useState({
    host: '',
    port: 5432,
    user: '',
    password: '',
    database: ''
  });
  const [bigqueryConfig, setBigqueryConfig] = useState({
    project_id: '',
    dataset_id: '',
    credentials_path: '',
    credentials_filename: ''
  });
  const [icebergConfig, setIcebergConfig] = useState({
    region: '',
    s3_staging: '',
    database: '',
    catalog: 'AwsDataCatalog',
    workgroup: 'primary',
    credentials_path: '',
    credentials_filename: ''
  });
  const [isUploading, setIsUploading] = useState(false);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [schemaRes, metadataRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/schema`),
        axios.get(`${API_BASE_URL}/schema/metadata`)
      ]);

      const persistentMetadata = metadataRes.data || {};
      const items: SchemaItem[] = [];
      const measures = schemaRes.data.measures || {};
      const dimensions = schemaRes.data.dimensions || {};

      const descriptions: Record<string, string> = {};
      const polarities: Record<string, 'positive' | 'negative' | 'neutral'> = {};

      Object.entries(measures).forEach(([name, info]) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const itemInfo = info as any;
        const meta = persistentMetadata[name] || {};
        items.push({ 
          name, 
          type: 'measure', 
          title: itemInfo.title || name,
          description: itemInfo.description || '',
          cube: itemInfo.cube || '',
          polarity: meta.polarity || 'neutral' 
        });
        if (meta.description) descriptions[name] = meta.description;
        polarities[name] = meta.polarity || 'neutral';
      });

      Object.entries(dimensions).forEach(([name, info]) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const itemInfo = info as any;
        const meta = persistentMetadata[name] || {};
        items.push({ 
          name, 
          type: 'dimension', 
          title: itemInfo.title || name,
          description: itemInfo.description || '',
          cube: itemInfo.cube || ''
        });
        if (meta.description) descriptions[name] = meta.description;
      });

      setSchemaItems(items);
      setEditedDescriptions(descriptions);
      setEditedPolarity(polarities);
      
      const configRes = await axios.get(`${API_BASE_URL}/config/database`);
      const { db_type, config } = configRes.data;
      setDbType(db_type || 'postgres');
      if (config.postgres) setPostgresConfig(config.postgres);
      if (config.bigquery) setBigqueryConfig(config.bigquery);
      if (config.iceberg) setIcebergConfig(config.iceberg);

    } catch (error) {
      console.error('Failed to fetch data:', error);
      toast.error(t('settings.schema.save_failed'));
    } finally {
      setIsLoading(false);
    }
  }, [t]);

  useEffect(() => {
    if (open) {
      fetchData();
    }
  }, [open, fetchData]);

  const handleDescriptionChange = (name: string, value: string) => {
    setEditedDescriptions(prev => ({ ...prev, [name]: value }));
  };

  const handlePolarityChange = (name: string, value: 'positive' | 'negative' | 'neutral') => {
    setEditedPolarity(prev => ({ ...prev, [name]: value }));
  };

  const handleSave = async () => {
    const itemsToSave = schemaItems.map(item => ({
      name: item.name,
      type: item.type,
      description: editedDescriptions[item.name] || '',
      polarity: editedPolarity[item.name] || 'neutral'
    })).filter(item => item.description || item.polarity !== 'neutral');

    if (itemsToSave.length === 0) {
      toast.info(t('settings.schema.no_changes'));
      return;
    }

    setIsSaving(true);
    try {
      await axios.post(`${API_BASE_URL}/schema/metadata`, { metadata: itemsToSave });
      toast.success(t('settings.schema.save_success'));
      fetchData();
    } catch (error) {
      console.error('Save failed:', error);
      toast.error(t('settings.schema.save_failed'));
    } finally {
      setIsSaving(false);
    }
  };

  const handleClearAllTraining = async () => {
    if (!confirm(t('settings.database.reset_confirm'))) return;
    setIsLoading(true);
    try {
      await axios.delete(`${API_BASE_URL}/schema/training/all/everything`);
      toast.success(t('settings.schema.reset_success'));
      await fetchData();
    } catch {
      toast.error(t('settings.schema.reset_failed'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveDatabase = async () => {
    setIsSaving(true);
    try {
      let configData = {};
      if (dbType === 'postgres') configData = postgresConfig;
      if (dbType === 'bigquery') configData = bigqueryConfig;
      if (dbType === 'iceberg') configData = icebergConfig;

      await axios.post(`${API_BASE_URL}/config/database`, { 
        db_type: dbType,
        config_data: configData 
      });
      toast.success(t('settings.database.save_success') || 'Database configuration saved');
      await fetchData(); 
      setActiveTab('schema');
    } catch (error) {
      console.error('DB Config Save failed:', error);
      toast.error(t('settings.schema.save_failed'));
    } finally {
      setIsSaving(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>, target: 'bigquery' | 'iceberg') => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_BASE_URL}/config/credentials/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      if (target === 'bigquery') {
        setBigqueryConfig(prev => ({ 
          ...prev, 
          credentials_path: response.data.file_path,
          credentials_filename: response.data.filename 
        }));
      } else {
        setIcebergConfig(prev => ({ 
          ...prev, 
          credentials_path: response.data.file_path,
          credentials_filename: response.data.filename
        }));
      }
      toast.success('認証ファイルをアップロードしました');
    } catch (error) {
      console.error('Upload failed:', error);
      toast.error('ファイルのアップロードに失敗しました');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl h-[85vh] flex flex-col overflow-hidden">
        <DialogHeader className="shrink-0">
          <DialogTitle className="flex items-center gap-2 text-xl">
            <Database className="w-6 h-6 text-blue-600" />
            {t('settings.title')}
          </DialogTitle>
          <DialogDescription>
            {t('settings.description')}
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 min-h-0 flex flex-col">
          <TabsList className="grid w-full grid-cols-3 shrink-0">
            <TabsTrigger value="database">{t('settings.tabs.database')}</TabsTrigger>
            <TabsTrigger value="schema">{t('settings.tabs.schema')}</TabsTrigger>
            <TabsTrigger value="language">{t('settings.tabs.language')}</TabsTrigger>
          </TabsList>

          <TabsContent value="database" className="flex-1 min-h-0 pt-4 flex flex-col">
            <Card className="flex-1 min-h-0 overflow-auto">
              <CardContent className="pt-6 space-y-6">
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-slate-700">{t('settings.database.type')}</label>
                  <div className="flex gap-2">
                    {(['postgres', 'bigquery', 'iceberg'] as const).map((type) => (
                      <Button
                        key={type}
                        variant={dbType === type ? 'default' : 'outline'}
                        onClick={() => setDbType(type)}
                        className="flex-1 capitalize"
                        size="sm"
                      >
                        {type === 'postgres' ? 'PostgreSQL' : type === 'bigquery' ? 'BigQuery' : 'AWS Iceberg'}
                      </Button>
                    ))}
                  </div>
                </div>

                {dbType === 'postgres' && (
                  <div className="grid grid-cols-2 gap-4 animate-in fade-in slide-in-from-top-1">
                    <div className="space-y-2 col-span-2">
                      <label className="text-xs font-medium text-slate-500">{t('settings.database.host')}</label>
                      <Input 
                        placeholder="localhost or remote-host.com" 
                        value={postgresConfig.host}
                        onChange={(e) => setPostgresConfig({...postgresConfig, host: e.target.value})}
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-slate-500">{t('settings.database.port')}</label>
                      <Input 
                        type="number"
                        placeholder="5432" 
                        value={postgresConfig.port}
                        onChange={(e) => setPostgresConfig({...postgresConfig, port: parseInt(e.target.value)})}
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-slate-500">{t('settings.database.dbname')}</label>
                      <Input 
                        placeholder="chatbi" 
                        value={postgresConfig.database}
                        onChange={(e) => setPostgresConfig({...postgresConfig, database: e.target.value})}
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-slate-500">{t('settings.database.user')}</label>
                      <Input 
                        placeholder="postgres" 
                        value={postgresConfig.user}
                        onChange={(e) => setPostgresConfig({...postgresConfig, user: e.target.value})}
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-slate-500">{t('settings.database.password')}</label>
                      <Input 
                        type="password"
                        placeholder="••••••••" 
                        value={postgresConfig.password}
                        onChange={(e) => setPostgresConfig({...postgresConfig, password: e.target.value})}
                      />
                    </div>
                  </div>
                )}

                {dbType === 'bigquery' && (
                  <div className="space-y-4 animate-in fade-in slide-in-from-top-1">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label className="text-xs font-medium text-slate-500">{t('settings.database.project_id')}</label>
                        <Input 
                          placeholder="your-project-id" 
                          value={bigqueryConfig.project_id}
                          onChange={(e) => setBigqueryConfig({...bigqueryConfig, project_id: e.target.value})}
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-xs font-medium text-slate-500">{t('settings.database.dataset_id')}</label>
                        <Input 
                          placeholder="your_dataset" 
                          value={bigqueryConfig.dataset_id}
                          onChange={(e) => setBigqueryConfig({...bigqueryConfig, dataset_id: e.target.value})}
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-slate-500">{t('settings.database.credentials')}</label>
                      <div className="flex items-center gap-2">
                        <Input 
                          type="file" 
                          accept=".json" 
                          onChange={(e) => handleFileUpload(e, 'bigquery')}
                          className="text-xs h-9 cursor-pointer"
                        />
                      </div>
                      {bigqueryConfig.credentials_filename && (
                        <div className="flex items-center gap-2 text-xs text-green-600 bg-green-50 p-2 rounded border border-green-100">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>{t('settings.database.uploaded')}: {bigqueryConfig.credentials_filename}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {dbType === 'iceberg' && (
                  <div className="space-y-4 animate-in fade-in slide-in-from-top-1">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label className="text-xs font-medium text-slate-500">{t('settings.database.region')}</label>
                        <Input 
                          placeholder="ap-northeast-1" 
                          value={icebergConfig.region}
                          onChange={(e) => setIcebergConfig({...icebergConfig, region: e.target.value})}
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-xs font-medium text-slate-500">{t('settings.database.s3_staging')}</label>
                        <Input 
                          placeholder="s3://your-bucket/staging/" 
                          value={icebergConfig.s3_staging}
                          onChange={(e) => setIcebergConfig({...icebergConfig, s3_staging: e.target.value})}
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-xs font-medium text-slate-500">{t('settings.database.dbname')}</label>
                        <Input 
                          placeholder="iceberg_db" 
                          value={icebergConfig.database}
                          onChange={(e) => setIcebergConfig({...icebergConfig, database: e.target.value})}
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-xs font-medium text-slate-500">{t('settings.database.workgroup')}</label>
                        <Input 
                          placeholder="primary" 
                          value={icebergConfig.workgroup}
                          onChange={(e) => setIcebergConfig({...icebergConfig, workgroup: e.target.value})}
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-slate-500">{t('settings.database.credentials')}</label>
                      <Input 
                        type="file" 
                        onChange={(e) => handleFileUpload(e, 'iceberg')}
                        className="text-xs h-9 cursor-pointer"
                      />
                      {icebergConfig.credentials_filename && (
                        <div className="flex items-center gap-2 text-xs text-green-600 bg-green-50 p-2 rounded border border-green-100">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>{t('settings.database.uploaded')}: {icebergConfig.credentials_filename}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                <Button onClick={handleSaveDatabase} disabled={isSaving || isUploading} className="w-full bg-blue-600 hover:bg-blue-700">
                  {isSaving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                  {t('settings.database.save')}
                </Button>

                <div className="pt-8 border-t">
                  <h4 className="text-sm font-medium text-red-600 mb-2">{t('settings.database.maintenance')}</h4>
                  <p className="text-xs text-slate-500 mb-4">
                    {t('settings.database.reset_description')}
                  </p>
                  <Button variant="outline" size="sm" onClick={handleClearAllTraining} className="text-red-600 border-red-200 hover:bg-red-50">
                    <RotateCcw className="w-4 h-4 mr-2" />
                    {t('settings.database.reset_button')}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="schema" className="flex-1 min-h-0 flex flex-col pt-4 overflow-hidden">
            <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 flex items-start gap-3 text-sm text-blue-800 shrink-0 mb-4">
              <Info className="w-5 h-5 shrink-0 mt-0.5" />
              <p>{t('settings.schema.info_box')}</p>
            </div>

            <div className="flex-1 min-h-0 border rounded-lg bg-white flex flex-col">
              <ScrollArea className="flex-1 overflow-auto">
                <table className="w-full text-sm text-left border-collapse min-w-[800px]">
                  <thead className="bg-slate-50 sticky top-0 z-20 shadow-sm">
                    <tr>
                      <th className="px-4 py-3 font-semibold text-slate-700 border-b w-[200px]">{t('settings.schema.column_name')}</th>
                      <th className="px-4 py-3 font-semibold text-slate-700 border-b w-[200px]">{t('settings.schema.current_desc')}</th>
                      <th className="px-4 py-3 font-semibold text-slate-700 border-b">{t('settings.schema.ai_desc')}</th>
                      <th className="px-4 py-3 font-semibold text-slate-700 border-b w-[180px]">{t('settings.schema.polarity')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {isLoading ? (
                      <tr><td colSpan={4} className="text-center py-20"><Loader2 className="w-8 h-8 animate-spin mx-auto mb-2 text-blue-500" />読み込み中...</td></tr>
                    ) : schemaItems.map((item) => (
                      <tr key={item.name} className="hover:bg-slate-50/50 transition-colors">
                        <td className="px-4 py-3 align-top">
                          <div className="font-mono text-xs font-medium truncate max-w-[180px]" title={item.name}>{item.name}</div>
                          <Badge variant={item.type === 'measure' ? 'default' : 'secondary'} className="mt-1 text-[10px]">
                            {item.type}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 align-top text-slate-400 text-xs italic">
                          {item.description || item.title || t('settings.schema.no_desc')}
                        </td>
                        <td className="px-4 py-3 align-top">
                          <Input 
                            placeholder={t('settings.schema.ai_desc_placeholder')}
                            value={editedDescriptions[item.name] ?? ''}
                            onChange={(e) => handleDescriptionChange(item.name, e.target.value)}
                            className="bg-transparent border-slate-200 focus:bg-white h-8 text-xs"
                          />
                        </td>
                        <td className="px-4 py-3 align-top">
                          {(item.type === 'measure' || 
                            item.name.toLowerCase().includes('total') || 
                            item.name.toLowerCase().includes('amount') || 
                            item.name.toLowerCase().includes('spent') ||
                            item.name.toLowerCase().includes('price') ||
                            item.name.toLowerCase().includes('quantity') ||
                            item.name.toLowerCase().includes('count')
                           ) ? (
                            <div className="flex bg-slate-100 p-0.5 rounded-md">
                              {(['positive', 'neutral', 'negative'] as const).map((p) => (
                                <button
                                  key={p}
                                  onClick={() => handlePolarityChange(item.name, p)}
                                  className={`flex-1 px-1 py-1 rounded text-[10px] capitalize transition-all ${
                                    (editedPolarity[item.name] || 'neutral') === p
                                      ? p === 'positive' ? 'bg-green-500 text-white' : 
                                        p === 'negative' ? 'bg-red-500 text-white' : 
                                        'bg-white text-slate-600 shadow-sm'
                                      : 'text-slate-500 hover:text-slate-700'
                                  }`}
                                >
                                  {p === 'positive' ? t('settings.schema.polarity_positive') : p === 'negative' ? t('settings.schema.polarity_negative') : t('settings.schema.polarity_neutral')}
                                </button>
                              ))}
                            </div>
                          ) : (
                            <span className="text-slate-300 text-[10px]">-</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </ScrollArea>
            </div>
            
            <div className="flex justify-end pt-4 shrink-0">
              <Button onClick={handleSave} disabled={isSaving} className="px-8 bg-blue-600 hover:bg-blue-700 shadow-md">
                {isSaving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                {t('settings.schema.save_and_train')}
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="language" className="flex-1 min-h-0 pt-4 flex flex-col">
            <Card className="flex-1 min-h-0">
              <CardContent className="pt-6 space-y-6">
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-slate-700">{t('settings.language.select')}</label>
                  <div className="grid grid-cols-2 gap-4">
                    <Button
                      variant={i18n.language === 'ja' ? 'default' : 'outline'}
                      onClick={() => i18n.changeLanguage('ja')}
                      className="w-full"
                    >
                      {t('settings.language.ja')}
                    </Button>
                    <Button
                      variant={i18n.language === 'en' ? 'default' : 'outline'}
                      onClick={() => i18n.changeLanguage('en')}
                      className="w-full"
                    >
                      {t('settings.language.en')}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
