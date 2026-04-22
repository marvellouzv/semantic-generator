import { useEffect, useCallback } from 'react'

export interface KeyboardShortcut {
  key: string
  ctrlKey?: boolean
  shiftKey?: boolean
  altKey?: boolean
  metaKey?: boolean
  action: () => void
  description: string
  preventDefault?: boolean
}

export interface UseKeyboardShortcutsOptions {
  shortcuts: KeyboardShortcut[]
  enabled?: boolean
  target?: HTMLElement | null
}

export function useKeyboardShortcuts({
  shortcuts,
  enabled = true,
  target
}: UseKeyboardShortcutsOptions) {
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!enabled) return

    const pressedKey = event.key.toLowerCase()
    const isCtrl = event.ctrlKey || event.metaKey
    const isShift = event.shiftKey
    const isAlt = event.altKey

    for (const shortcut of shortcuts) {
      const shortcutKey = shortcut.key.toLowerCase()
      const matchesKey = pressedKey === shortcutKey
      const matchesCtrl = (shortcut.ctrlKey || shortcut.metaKey) === isCtrl
      const matchesShift = shortcut.shiftKey === isShift
      const matchesAlt = shortcut.altKey === isAlt

      if (matchesKey && matchesCtrl && matchesShift && matchesAlt) {
        if (shortcut.preventDefault !== false) {
          event.preventDefault()
        }
        shortcut.action()
        break
      }
    }
  }, [shortcuts, enabled])

  useEffect(() => {
    const targetElement = target || document
    targetElement.addEventListener('keydown', handleKeyDown)
    
    return () => {
      targetElement.removeEventListener('keydown', handleKeyDown)
    }
  }, [handleKeyDown, target])
}

// Предустановленные горячие клавиши для приложения
export const APP_SHORTCUTS: KeyboardShortcut[] = [
  {
    key: 'e',
    ctrlKey: true,
    action: () => {
      // Экспорт - будет переопределено в компонентах
      console.log('Export shortcut triggered')
    },
    description: 'Экспорт данных',
    preventDefault: true
  },
  {
    key: 's',
    ctrlKey: true,
    action: () => {
      // Сохранение шаблона - будет переопределено в компонентах
      console.log('Save template shortcut triggered')
    },
    description: 'Сохранить как шаблон',
    preventDefault: true
  },
  {
    key: 'f',
    ctrlKey: true,
    action: () => {
      // Поиск - будет переопределено в компонентах
      console.log('Search shortcut triggered')
    },
    description: 'Открыть поиск',
    preventDefault: true
  },
  {
    key: 'h',
    ctrlKey: true,
    action: () => {
      // История - будет переопределено в компонентах
      console.log('History shortcut triggered')
    },
    description: 'Открыть историю',
    preventDefault: true
  },
  {
    key: 't',
    ctrlKey: true,
    action: () => {
      // Шаблоны - будет переопределено в компонентах
      console.log('Templates shortcut triggered')
    },
    description: 'Открыть шаблоны',
    preventDefault: true
  },
  {
    key: '?',
    action: () => {
      // Помощь - будет переопределено в компонентах
      console.log('Help shortcut triggered')
    },
    description: 'Показать справку по горячим клавишам',
    preventDefault: true
  },
  {
    key: 'Escape',
    action: () => {
      // Закрыть модальные окна - будет переопределено в компонентах
      console.log('Escape shortcut triggered')
    },
    description: 'Закрыть модальное окно',
    preventDefault: false
  }
]

// Хук для управления фокусом
export function useFocusManagement() {
  const trapFocus = useCallback((element: HTMLElement) => {
    const focusableElements = element.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    ) as NodeListOf<HTMLElement>
    
    const firstElement = focusableElements[0]
    const lastElement = focusableElements[focusableElements.length - 1]

    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key === 'Tab') {
        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            lastElement.focus()
            e.preventDefault()
          }
        } else {
          if (document.activeElement === lastElement) {
            firstElement.focus()
            e.preventDefault()
          }
        }
      }
    }

    element.addEventListener('keydown', handleTabKey)
    
    return () => {
      element.removeEventListener('keydown', handleTabKey)
    }
  }, [])

  const focusFirstElement = useCallback((element: HTMLElement) => {
    const focusableElement = element.querySelector(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    ) as HTMLElement
    
    if (focusableElement) {
      focusableElement.focus()
    }
  }, [])

  return { trapFocus, focusFirstElement }
}

// Хук для ARIA-атрибутов
export function useAriaAttributes() {
  const getAriaProps = useCallback((role: string, options: Record<string, any> = {}) => {
    const baseProps = {
      role,
      ...options
    }

    // Добавляем стандартные ARIA-атрибуты в зависимости от роли
    switch (role) {
      case 'button':
        return {
          ...baseProps,
          tabIndex: 0,
          'aria-pressed': options.pressed || false
        }
      case 'dialog':
        return {
          ...baseProps,
          'aria-modal': true,
          'aria-labelledby': options.labelledBy
        }
      case 'tablist':
        return {
          ...baseProps,
          role: 'tablist'
        }
      case 'tab':
        return {
          ...baseProps,
          role: 'tab',
          'aria-selected': options.selected || false,
          'aria-controls': options.controls
        }
      case 'tabpanel':
        return {
          ...baseProps,
          role: 'tabpanel',
          'aria-labelledby': options.labelledBy
        }
      default:
        return baseProps
    }
  }, [])

  return { getAriaProps }
}
