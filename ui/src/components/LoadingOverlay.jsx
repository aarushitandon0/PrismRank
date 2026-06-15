import { AnimatePresence, motion } from 'framer-motion'

export default function LoadingOverlay({ visible, message }) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center ml-60"
          style={{ background: 'rgba(12,10,8,0.92)' }}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            transition={{ type: 'spring', damping: 20 }}
            className="text-center"
          >
            {/* Prism spinner */}
            <div className="relative w-16 h-16 mx-auto mb-8">
              <svg className="animate-spin-slow w-16 h-16" viewBox="0 0 64 64" fill="none">
                <path d="M32 4L60 20V44L32 60L4 44V20L32 4Z"
                  stroke="url(#grad)" strokeWidth="1.5" strokeLinejoin="round" opacity="0.3"/>
                <path d="M32 4L60 20" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round"/>
                <defs>
                  <linearGradient id="grad" x1="4" y1="4" x2="60" y2="60" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#f59e0b"/>
                    <stop offset="1" stopColor="#d97706" stopOpacity="0"/>
                  </linearGradient>
                </defs>
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-amber-500" />
              </div>
            </div>

            <AnimatePresence mode="wait">
              <motion.p
                key={message}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                className="text-stone-200 text-base font-medium font-display"
              >
                {message}
              </motion.p>
            </AnimatePresence>
            <p className="text-stone-600 text-sm mt-2">PrismRank is processing your talent pool</p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
