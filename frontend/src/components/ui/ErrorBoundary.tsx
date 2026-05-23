import { AlertTriangle } from "lucide-react";
import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}
interface State {
  hasError: boolean;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-gray-500 px-4">
          <div className="w-16 h-16 rounded-full bg-orange-50 flex items-center justify-center">
            <AlertTriangle size={32} className="text-orange-400" />
          </div>
          <div className="text-center">
            <h2 className="font-poppins font-bold text-[#263238] text-lg mb-1">
              Algo salió mal
            </h2>
            <p className="text-sm text-gray-400 mb-4">
              Ocurrió un error inesperado. Intenta recargar la página.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-5 py-2 bg-[#00bfa5] text-white text-sm font-medium rounded-xl hover:bg-brand-hover transition"
            >
              Recargar página
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
