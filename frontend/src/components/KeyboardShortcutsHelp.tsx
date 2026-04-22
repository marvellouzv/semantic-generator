import React from 'react'
import { X, Command, ArrowUp, Option } from 'lucide-react'
import type { KeyboardShortcut } from '../hooks/useKeyboardShortcuts'

interface Props {
  shortcuts: KeyboardShortcut[]
  onClose: () => void
}

export default function KeyboardShortcutsHelp({ shortcuts, onClose }: Props) {
  const getKeyIcon = (key: string) => {
    switch (key.toLowerCase()) {
      case 'ctrl':
      case 'meta':
        return <Command size={14} />
      case 'shift':
        return <ArrowUp size={14} />
      case 'alt':
        return <Option size={14} />
      default:
        return <span className="text-xs font-mono">{key.toUpperCase()}</span>
    }
  }

  const formatShortcut = (shortcut: KeyboardShortcut) => {
    const keys = []
    
    if (shortcut.ctrlKey || shortcut.metaKey) {
      keys.push({ key: 'Ctrl', icon: getKeyIcon('ctrl') })
    }
    if (shortcut.altKey) {
      keys.push({ key: 'Alt', icon: getKeyIcon('alt') })
    }
    if (shortcut.shiftKey) {
      keys.push({ key: 'Shift', icon: getKeyIcon('shift') })
    }
    
    keys.push({ key: shortcut.key, icon: getKeyIcon(shortcut.key) })
    
    return keys
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div 
        className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="shortcuts-title"
      >
        <div className="flex justify-between items-center p-4 border-b">
          <h2 id="shortcuts-title" className="text-xl font-semibold">
            Горячие клавиши
          </h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
            aria-label="Закрыть справку"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-4 overflow-y-auto max-h-[calc(90vh-80px)]">
          <div className="space-y-4">
            {shortcuts.map((shortcut, index) => {
              const formattedKeys = formatShortcut(shortcut)
              
              return (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex-1">
                    <div className="font-medium text-gray-900">
                      {shortcut.description}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-1">
                    {formattedKeys.map((keyInfo, keyIndex) => (
                      <React.Fragment key={keyIndex}>
                        <div className="flex items-center gap-1 px-2 py-1 bg-white border border-gray-300 rounded text-sm font-mono">
                          {keyInfo.icon}
                          <span>{keyInfo.key}</span>
                        </div>
                        {keyIndex < formattedKeys.length - 1 && (
                          <span className="text-gray-400">+</span>
                        )}
                      </React.Fragment>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
          
          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h3 className="font-medium text-blue-900 mb-2">Советы по использованию</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• Горячие клавиши работают только когда фокус находится в основном интерфейсе</li>
              <li>• В модальных окнах используйте Tab для навигации между элементами</li>
              <li>• Нажмите Escape для закрытия любого модального окна</li>
              <li>• Ctrl+E работает для экспорта в любом месте приложения</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
