export interface ApiErrorAlertProps {
  error: string;
}

export function ApiErrorAlert({ error }: ApiErrorAlertProps) {
  return (
    <div className={`api-error-alert${error ? "" : " hidden"}`} id="api-error-alert" role="alert">
      {error}
    </div>
  );
}
